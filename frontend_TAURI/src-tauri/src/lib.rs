use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::collections::HashMap;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const MAX_SOURCE_BYTES: usize = 100_000;
const MAX_CASES: usize = 250;
const MAX_INPUT_BYTES: usize = 2 * 1024 * 1024;
const MAX_DIAGNOSTICS_BYTES: usize = 20_000;
const MAX_STREAM_BYTES: usize = 64 * 1024;
const MAX_CASE_OUTPUT_BYTES: usize = 128 * 1024;
const MAX_SUBMISSION_OUTPUT_BYTES: usize = 1_000_000;
const COMPILE_TIMEOUT: Duration = Duration::from_secs(120);
const RUNNER_VERSION: &str = "0.1.0";

#[derive(Debug, Deserialize)]
struct ExecutionCase {
    id: String,
    #[serde(default)]
    input: String,
    time_limit_seconds: Option<u64>,
}

#[derive(Debug, Serialize)]
struct CompilationResult {
    status: &'static str,
    duration_ms: u64,
    diagnostics: String,
}

#[derive(Debug, Serialize)]
struct TestResult {
    test_case_id: String,
    status: &'static str,
    exit_code: Option<i32>,
    duration_ms: u64,
    stdout: String,
    stderr: String,
}

#[derive(Debug, Serialize)]
struct RunnerResponse {
    runner_type: &'static str,
    runner_version: &'static str,
    compiler_version: String,
    compilation: CompilationResult,
    test_results: Vec<TestResult>,
}

#[derive(Default)]
struct CapturedOutput {
    stdout: Vec<u8>,
    stderr: Vec<u8>,
}

struct ProcessOutput {
    status: ExitStatus,
    timed_out: bool,
    cancelled: bool,
    output_limited: bool,
    captured: CapturedOutput,
}

#[derive(Default)]
struct RunnerState {
    active_runs: Mutex<HashMap<String, Arc<AtomicBool>>>,
}

struct TempWorkspace(PathBuf);

impl Drop for TempWorkspace {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

static TEMP_SEQUENCE: AtomicU64 = AtomicU64::new(0);

#[cfg(target_os = "windows")]
struct ProcessJob {
    handle: *mut std::ffi::c_void,
}

#[cfg(not(target_os = "windows"))]
struct ProcessJob;

#[cfg(target_os = "windows")]
#[repr(C)]
#[derive(Default)]
struct JobBasicLimitInformation {
    per_process_user_time_limit: i64,
    per_job_user_time_limit: i64,
    limit_flags: u32,
    minimum_working_set_size: usize,
    maximum_working_set_size: usize,
    active_process_limit: u32,
    affinity: usize,
    priority_class: u32,
    scheduling_class: u32,
}

#[cfg(target_os = "windows")]
#[repr(C)]
#[derive(Default)]
struct JobIoCounters {
    read_operation_count: u64,
    write_operation_count: u64,
    other_operation_count: u64,
    read_transfer_count: u64,
    write_transfer_count: u64,
    other_transfer_count: u64,
}

#[cfg(target_os = "windows")]
#[repr(C)]
#[derive(Default)]
struct JobExtendedLimitInformation {
    basic_limit_information: JobBasicLimitInformation,
    io_info: JobIoCounters,
    process_memory_limit: usize,
    job_memory_limit: usize,
    peak_process_memory_used: usize,
    peak_job_memory_used: usize,
}

#[cfg(target_os = "windows")]
#[repr(C)]
struct ThreadEntry32 {
    size: u32,
    usage_count: u32,
    thread_id: u32,
    owner_process_id: u32,
    base_priority: i32,
    priority_delta: i32,
    flags: u32,
}

#[cfg(target_os = "windows")]
#[link(name = "kernel32")]
extern "system" {
    fn CreateJobObjectW(attributes: *const std::ffi::c_void, name: *const u16) -> *mut std::ffi::c_void;
    fn SetInformationJobObject(
        job: *mut std::ffi::c_void,
        information_class: i32,
        information: *const std::ffi::c_void,
        information_length: u32,
    ) -> i32;
    fn AssignProcessToJobObject(job: *mut std::ffi::c_void, process: *mut std::ffi::c_void) -> i32;
    fn TerminateJobObject(job: *mut std::ffi::c_void, exit_code: u32) -> i32;
    fn CloseHandle(handle: *mut std::ffi::c_void) -> i32;
    fn CreateToolhelp32Snapshot(flags: u32, process_id: u32) -> *mut std::ffi::c_void;
    fn Thread32First(snapshot: *mut std::ffi::c_void, entry: *mut ThreadEntry32) -> i32;
    fn Thread32Next(snapshot: *mut std::ffi::c_void, entry: *mut ThreadEntry32) -> i32;
    fn OpenThread(access: u32, inherit: i32, thread_id: u32) -> *mut std::ffi::c_void;
    fn ResumeThread(thread: *mut std::ffi::c_void) -> u32;
}

#[cfg(target_os = "windows")]
impl ProcessJob {
    fn create() -> Result<Self, String> {
        const JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS: i32 = 9;
        const JOB_OBJECT_LIMIT_ACTIVE_PROCESS: u32 = 0x0000_0008;
        const JOB_OBJECT_LIMIT_PROCESS_MEMORY: u32 = 0x0000_0100;
        const JOB_OBJECT_LIMIT_JOB_MEMORY: u32 = 0x0000_0200;
        const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x0000_2000;

        let handle = unsafe { CreateJobObjectW(std::ptr::null(), std::ptr::null()) };
        if handle.is_null() {
            return Err(format!("Could not create a Windows process job: {}", std::io::Error::last_os_error()));
        }

        let job = Self { handle };
        let mut limits = JobExtendedLimitInformation::default();
        limits.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | JOB_OBJECT_LIMIT_JOB_MEMORY
            | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        limits.basic_limit_information.active_process_limit = 16;
        limits.process_memory_limit = 512 * 1024 * 1024;
        limits.job_memory_limit = 512 * 1024 * 1024;

        let configured = unsafe {
            SetInformationJobObject(
                job.handle,
                JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                &limits as *const _ as *const std::ffi::c_void,
                std::mem::size_of::<JobExtendedLimitInformation>() as u32,
            )
        };
        if configured == 0 {
            let error = std::io::Error::last_os_error();
            drop(job);
            return Err(format!("Could not configure Windows process limits: {error}"));
        }
        Ok(job)
    }

    fn assign(&self, child: &Child) -> Result<(), String> {
        use std::os::windows::io::AsRawHandle;
        let assigned = unsafe {
            AssignProcessToJobObject(self.handle, child.as_raw_handle() as *mut std::ffi::c_void)
        };
        if assigned == 0 {
            return Err(format!("Could not attach the process to its Windows job: {}", std::io::Error::last_os_error()));
        }
        Ok(())
    }

    fn resume_primary_thread(&self, child: &Child) -> Result<(), String> {
        const TH32CS_SNAPTHREAD: u32 = 0x0000_0004;
        const THREAD_SUSPEND_RESUME: u32 = 0x0002;
        const CREATE_TOOLHELP_INVALID_HANDLE: isize = -1;
        const RESUME_THREAD_FAILED: u32 = u32::MAX;

        let snapshot = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0) };
        if snapshot as isize == CREATE_TOOLHELP_INVALID_HANDLE {
            return Err(format!("Could not inspect the suspended process: {}", std::io::Error::last_os_error()));
        }

        let mut entry: ThreadEntry32 = unsafe { std::mem::zeroed() };
        entry.size = std::mem::size_of::<ThreadEntry32>() as u32;
        let mut found = unsafe { Thread32First(snapshot, &mut entry) };
        let mut primary_thread_id = None;
        while found != 0 {
            if entry.owner_process_id == child.id() {
                primary_thread_id = Some(entry.thread_id);
                break;
            }
            found = unsafe { Thread32Next(snapshot, &mut entry) };
        }
        unsafe { CloseHandle(snapshot) };

        let thread_id = primary_thread_id.ok_or_else(|| "Could not find the suspended process thread.".to_string())?;
        let thread = unsafe { OpenThread(THREAD_SUSPEND_RESUME, 0, thread_id) };
        if thread.is_null() {
            return Err(format!("Could not open the suspended process thread: {}", std::io::Error::last_os_error()));
        }
        let resumed = unsafe { ResumeThread(thread) };
        let resume_error = if resumed == RESUME_THREAD_FAILED {
            Some(std::io::Error::last_os_error())
        } else {
            None
        };
        unsafe { CloseHandle(thread) };
        if let Some(error) = resume_error {
            return Err(format!("Could not start the process inside its Windows job: {error}"));
        }
        Ok(())
    }

    fn terminate(&self) {
        let _ = unsafe { TerminateJobObject(self.handle, 1) };
    }
}

#[cfg(target_os = "windows")]
impl Drop for ProcessJob {
    fn drop(&mut self) {
        let _ = unsafe { CloseHandle(self.handle) };
    }
}

#[cfg(not(target_os = "windows"))]
impl ProcessJob {
    fn create() -> Result<Self, String> {
        Ok(Self)
    }

    fn assign(&self, _child: &Child) -> Result<(), String> {
        Ok(())
    }

    fn resume_primary_thread(&self, _child: &Child) -> Result<(), String> {
        Ok(())
    }

    fn terminate(&self) {}
}

#[tauri::command]
fn detect_gcc() -> Result<String, String> {
    let compiler = compiler_program();
    let output = Command::new(&compiler)
        .arg("--version")
        .output()
        .map_err(|error| format!(
            "Could not start GCC at {}: {error}. Install GCC and add it to PATH, or set GEETA_GCC_PATH to gcc.exe.",
            compiler.display()
        ))?;

    if !output.status.success() {
        return Err("GCC could not report its version.".to_string());
    }

    let version_output = String::from_utf8_lossy(&output.stdout);
    Ok(version_output.lines().next().unwrap_or("GCC (version unknown)").to_string())
}

fn compiler_program() -> PathBuf {
    if let Some(configured_path) = std::env::var_os("GEETA_GCC_PATH").filter(|path| !path.is_empty()) {
        return PathBuf::from(configured_path);
    }

    let executable_name = if cfg!(windows) { "gcc.exe" } else { "gcc" };
    PathBuf::from(executable_name)
}

fn create_workspace() -> Result<TempWorkspace, String> {
    let root = std::env::temp_dir();
    for _ in 0..16 {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos();
        let sequence = TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let path = root.join(format!("geeta-assessment-{}-{timestamp}-{sequence}", std::process::id()));
        match fs::create_dir(&path) {
            Ok(()) => return Ok(TempWorkspace(path)),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(format!("Could not create a temporary compile folder: {error}")),
        }
    }
    Err("Could not reserve a unique temporary compile folder.".to_string())
}

impl TempWorkspace {
    fn path(&self) -> &Path {
        &self.0
    }
}

fn bounded_reader<R: Read + Send + 'static>(
    mut reader: R,
    stdout: bool,
    captured: Arc<Mutex<CapturedOutput>>,
    total_bytes: Arc<AtomicUsize>,
    max_total_bytes: usize,
    output_limit_reached: Arc<AtomicBool>,
) -> thread::JoinHandle<()> {
    thread::spawn(move || {
        let mut buffer = [0_u8; 8192];
        loop {
            let read = match reader.read(&mut buffer) {
                Ok(0) | Err(_) => break,
                Ok(read) => read,
            };
            let previous_total = total_bytes
                .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |total| {
                    Some(total.saturating_add(read).min(max_total_bytes))
                })
                .unwrap_or(max_total_bytes);
            let allowed_total = max_total_bytes.saturating_sub(previous_total).min(read);
            let Ok(mut captured) = captured.lock() else { break };
            let stream = if stdout { &mut captured.stdout } else { &mut captured.stderr };
            let allowed_stream = MAX_STREAM_BYTES.saturating_sub(stream.len()).min(allowed_total);
            stream.extend_from_slice(&buffer[..allowed_stream]);
            if allowed_stream < read {
                output_limit_reached.store(true, Ordering::Relaxed);
            }
        }
    })
}

fn collect_child_output(
    child: &mut Child,
    input: Option<String>,
    timeout: Duration,
    max_total_bytes: usize,
    cancellation: Arc<AtomicBool>,
    process_job: &ProcessJob,
) -> Result<ProcessOutput, String> {
    let captured = Arc::new(Mutex::new(CapturedOutput::default()));
    let total_bytes = Arc::new(AtomicUsize::new(0));
    let output_limit_reached = Arc::new(AtomicBool::new(false));
    let stdout = child.stdout.take().ok_or_else(|| "Could not capture process output.".to_string())?;
    let stderr = child.stderr.take().ok_or_else(|| "Could not capture process errors.".to_string())?;
    let stdout_reader = bounded_reader(
        stdout,
        true,
        Arc::clone(&captured),
        Arc::clone(&total_bytes),
        max_total_bytes,
        Arc::clone(&output_limit_reached),
    );
    let stderr_reader = bounded_reader(
        stderr,
        false,
        Arc::clone(&captured),
        Arc::clone(&total_bytes),
        max_total_bytes,
        Arc::clone(&output_limit_reached),
    );

    if let (Some(input), Some(mut stdin)) = (input, child.stdin.take()) {
        thread::spawn(move || {
            let _ = stdin.write_all(input.as_bytes());
        });
    }

    let started = Instant::now();
    let mut timed_out = false;
    let mut cancelled = false;
    let status = loop {
        if cancellation.load(Ordering::Relaxed) {
            cancelled = true;
            terminate_child_tree(child, process_job);
            break child.wait().map_err(|error| format!("Could not stop the cancelled program: {error}"))?;
        }
        if output_limit_reached.load(Ordering::Relaxed) {
            terminate_child_tree(child, process_job);
            break child.wait().map_err(|error| format!("Could not stop the output-limited program: {error}"))?;
        }
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if started.elapsed() < timeout => thread::sleep(Duration::from_millis(10)),
            Ok(None) => {
                timed_out = true;
                terminate_child_tree(child, process_job);
                break child.wait().map_err(|error| format!("Could not stop the timed-out program: {error}"))?;
            }
            Err(error) => {
                terminate_child_tree(child, process_job);
                let _ = child.wait();
                return Err(format!("Could not monitor the running program: {error}"));
            }
        }
    };

    // A submission only owns its main process. Stop any children it left behind
    // so inherited output pipes close, then collect all bytes still buffered.
    process_job.terminate();
    let _ = stdout_reader.join();
    let _ = stderr_reader.join();
    let captured = captured.lock()
        .map_err(|_| "Could not collect compiler output.".to_string())?;
    Ok(ProcessOutput {
        status,
        timed_out,
        cancelled,
        output_limited: output_limit_reached.load(Ordering::Relaxed),
        captured: CapturedOutput {
            stdout: captured.stdout.clone(),
            stderr: captured.stderr.clone(),
        },
    })
}

fn run_process(
    mut command: Command,
    input: Option<String>,
    timeout: Duration,
    max_output_bytes: usize,
    cancellation: Arc<AtomicBool>,
) -> Result<ProcessOutput, String> {
    command
        .stdin(if input.is_some() { Stdio::piped() } else { Stdio::null() })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let process_job = ProcessJob::create()?;
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0000_0004); // CREATE_SUSPENDED
    }
    let mut child = command.spawn().map_err(|error| format!("Could not start process: {error}"))?;
    if let Err(error) = process_job.assign(&child) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }
    if let Err(error) = process_job.resume_primary_thread(&child) {
        process_job.terminate();
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }
    collect_child_output(
        &mut child,
        input,
        timeout,
        max_output_bytes,
        cancellation,
        &process_job,
    )
}

fn terminate_child_tree(child: &mut Child, process_job: &ProcessJob) {
    process_job.terminate();
    let _ = child.kill();
}

fn append_bounded(destination: &mut Vec<u8>, source: &[u8], limit: usize) {
    let remaining = limit.saturating_sub(destination.len());
    destination.extend_from_slice(&source[..source.len().min(remaining)]);
}

fn elapsed_ms(started: Instant) -> u64 {
    started.elapsed().as_millis().min(u64::MAX as u128) as u64
}

fn decode_bounded(bytes: &[u8], max_bytes: usize) -> String {
    let text = String::from_utf8_lossy(bytes);
    if text.len() <= max_bytes {
        return text.into_owned();
    }
    let mut end = max_bytes;
    while !text.is_char_boundary(end) {
        end -= 1;
    }
    text[..end].to_string()
}

fn run_submission(
    source_code: String,
    test_cases: Vec<ExecutionCase>,
    default_time_limit_seconds: Option<u64>,
    compiler_program: PathBuf,
    cancellation: Arc<AtomicBool>,
) -> Result<RunnerResponse, String> {
    if source_code.is_empty() {
        return Err("Enter C source code before running this question.".to_string());
    }
    if source_code.len() > MAX_SOURCE_BYTES {
        return Err("Source code must be 100 KB or smaller.".to_string());
    }
    if test_cases.is_empty() || test_cases.len() > MAX_CASES {
        return Err(format!("Provide between 1 and {MAX_CASES} test cases."));
    }
    let total_input_bytes: usize = test_cases.iter().map(|test_case| test_case.input.len()).sum();
    if total_input_bytes > MAX_INPUT_BYTES {
        return Err("Test case inputs exceed the 2 MB execution limit.".to_string());
    }

    let compiler_output = Command::new(&compiler_program)
        .arg("--version")
        .output()
        .map_err(|error| format!("GCC is unavailable at {}: {error}", compiler_program.display()))?;
    if !compiler_output.status.success() {
        return Err("GCC could not report its version.".to_string());
    }
    let compiler_version = String::from_utf8_lossy(&compiler_output.stdout)
        .lines()
        .next()
        .unwrap_or("GCC (version unknown)")
        .to_string();
    let workspace = create_workspace()?;
    let source_path = workspace.path().join("main.c");
    let executable_path = workspace.path().join(if cfg!(windows) { "solution.exe" } else { "solution" });
    fs::write(&source_path, source_code.as_bytes())
        .map_err(|error| format!("Could not save the temporary C source: {error}"))?;

    let compile_started = Instant::now();
    let mut compiler = Command::new(&compiler_program);
    compiler
        .args(["-std=c11", "-O0", "-Wall", "-Wextra"])
        .arg(&source_path)
        .arg("-o")
        .arg(&executable_path)
        .current_dir(workspace.path());
    let compile = run_process(
        compiler,
        None,
        COMPILE_TIMEOUT,
        MAX_DIAGNOSTICS_BYTES,
        Arc::clone(&cancellation),
    )?;
    if compile.cancelled {
        return Err("The C execution was cancelled.".to_string());
    }
    let compile_duration_ms = elapsed_ms(compile_started);
    let mut diagnostics = compile.captured.stderr;
    append_bounded(&mut diagnostics, &compile.captured.stdout, MAX_DIAGNOSTICS_BYTES);

    if compile.timed_out || compile.output_limited || !compile.status.success() {
        if compile.timed_out {
            diagnostics = b"GCC exceeded the 120 second compile time limit.".to_vec();
        } else if compile.output_limited {
            diagnostics = b"GCC diagnostics exceeded the 20 KB limit.".to_vec();
        }
        return Ok(RunnerResponse {
            runner_type: "desktop_gcc",
            runner_version: RUNNER_VERSION,
            compiler_version,
            compilation: CompilationResult {
                status: "error",
                duration_ms: compile_duration_ms,
                diagnostics: String::from_utf8_lossy(&diagnostics).into_owned(),
            },
            test_results: Vec::new(),
        });
    }

    let mut remaining_output_bytes = MAX_SUBMISSION_OUTPUT_BYTES;
    let mut test_results = Vec::with_capacity(test_cases.len());
    for test_case in test_cases {
        if cancellation.load(Ordering::Relaxed) {
            return Err("The C execution was cancelled.".to_string());
        }
        let case_started = Instant::now();
        let time_limit = test_case.time_limit_seconds.or(default_time_limit_seconds).unwrap_or(10).clamp(1, 120);
        let output_limit = remaining_output_bytes.min(MAX_CASE_OUTPUT_BYTES);
        let mut execution = Command::new(&executable_path);
        execution.current_dir(workspace.path());
        let result = run_process(
            execution,
            Some(test_case.input),
            Duration::from_secs(time_limit),
            output_limit,
            Arc::clone(&cancellation),
        );
        let (status, exit_code, stdout, stderr) = match result {
            Ok(result) if result.cancelled => return Err("The C execution was cancelled.".to_string()),
            Ok(result) if result.timed_out => (
                "time_limit_exceeded",
                None,
                decode_bounded(&result.captured.stdout, MAX_STREAM_BYTES),
                "Execution exceeded the test case time limit.".to_string(),
            ),
            Ok(result) if result.output_limited => (
                "runtime_error",
                None,
                decode_bounded(&result.captured.stdout, MAX_STREAM_BYTES),
                format!("Program output exceeded the {} KB per-stream or {} KB combined limit.", MAX_STREAM_BYTES / 1024, MAX_CASE_OUTPUT_BYTES / 1024),
            ),
            Ok(result) => {
                let code = result.status.code();
                let text = decode_bounded(&result.captured.stdout, MAX_STREAM_BYTES);
                let error_text = decode_bounded(&result.captured.stderr, MAX_STREAM_BYTES);
                ("completed", code, text, error_text)
            }
            Err(error) => ("runtime_error", None, String::new(), error),
        };
        let captured_bytes = stdout.len().saturating_add(stderr.len()).min(remaining_output_bytes);
        remaining_output_bytes = remaining_output_bytes.saturating_sub(captured_bytes);
        test_results.push(TestResult {
            test_case_id: test_case.id,
            status,
            exit_code,
            duration_ms: elapsed_ms(case_started),
            stdout,
            stderr,
        });
    }

    Ok(RunnerResponse {
        runner_type: "desktop_gcc",
        runner_version: RUNNER_VERSION,
        compiler_version,
        compilation: CompilationResult {
            status: "success",
            duration_ms: compile_duration_ms,
            diagnostics: String::from_utf8_lossy(&diagnostics).into_owned(),
        },
        test_results,
    })
}

#[tauri::command]
async fn run_c_submission(
    state: tauri::State<'_, RunnerState>,
    run_id: String,
    source_code: String,
    test_cases: Vec<ExecutionCase>,
    time_limit_seconds: Option<u64>,
) -> Result<RunnerResponse, String> {
    let cancellation = Arc::new(AtomicBool::new(false));
    {
        let mut active_runs = state.active_runs
            .lock()
            .map_err(|_| "The local runner is unavailable.".to_string())?;
        if active_runs.contains_key(&run_id) {
            return Err("This desktop runner is already processing the request.".to_string());
        }
        active_runs.insert(run_id.clone(), Arc::clone(&cancellation));
    }

    let compiler_program = compiler_program();
    let result = tauri::async_runtime::spawn_blocking(move || {
        run_submission(source_code, test_cases, time_limit_seconds, compiler_program, cancellation)
    })
    .await;
    if let Ok(mut active_runs) = state.active_runs.lock() {
        active_runs.remove(&run_id);
    }
    result.map_err(|error| format!("The local C runner stopped unexpectedly: {error}"))?
}

#[tauri::command]
fn cancel_c_submission(state: tauri::State<'_, RunnerState>, run_id: String) {
    if let Ok(active_runs) = state.active_runs.lock() {
        if let Some(cancellation) = active_runs.get(&run_id) {
            cancellation.store(true, Ordering::Relaxed);
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(RunnerState::default())
        .invoke_handler(tauri::generate_handler![detect_gcc, run_c_submission, cancel_c_submission])
        .run(tauri::generate_context!())
        .expect("error while running Geeta Assessment Portal");
}
