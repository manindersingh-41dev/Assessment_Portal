import {
  CASE_STATUS,
  DEFAULT_COMPILE_TIMEOUT_MS,
  MAX_CASE_OUTPUT_BYTES,
  MAX_COMBINED_OUTPUT_BYTES,
  MAX_COMPILER_DIAGNOSTICS_BYTES,
  MAX_SUBMISSION_OUTPUT_BYTES,
  SUBMISSION_DIAGNOSTICS_RESERVE_BYTES,
  WASM_COMPILER_VERSION,
  WASM_RUNNER_VERSION,
  getUtf8ByteLength,
  normalizeTestCases,
  validateSourceCode,
} from '../runnerContract';

const assetBaseUrl = () => new URL(`${import.meta.env.BASE_URL}clang/`, window.location.origin).href;

const compilerWorkerUrl = new URL('./compiler.worker.js', import.meta.url);
const testcaseWorkerUrl = new URL('./testcase.worker.js', import.meta.url);

export class WasmRunner {
  constructor({ compileTimeoutMs = DEFAULT_COMPILE_TIMEOUT_MS } = {}) {
    this.compileTimeoutMs = compileTimeoutMs;
    this.activeWorkers = new Set();
    this.compilerWorker = null;
    this.pendingCompile = null;
    this.cancelRequested = false;
    this.type = 'web_wasm';
    this.version = WASM_RUNNER_VERSION;
    this.compilerVersion = WASM_COMPILER_VERSION;
  }

  async runSubmission({ sourceCode, testCases, timeLimitSeconds = 10, onStatus = () => {} }) {
    if (this.pendingCompile || this.activeWorkers.size > (this.compilerWorker ? 1 : 0)) {
      throw new Error('This runner is already processing another submission.');
    }

    this.cancelRequested = false;
    validateSourceCode(sourceCode);
    const cases = normalizeTestCases(testCases, timeLimitSeconds);
    const compilation = await this.#compile(sourceCode, onStatus);
    if (this.cancelRequested) throw new Error('The C execution was cancelled.');

    if (compilation.status === 'error') {
      return {
        runner_type: this.type,
        runner_version: this.version,
        compiler_version: this.compilerVersion,
        compilation: {
          status: 'error',
          duration_ms: compilation.durationMs,
          diagnostics: compilation.diagnostics,
        },
        test_results: [],
      };
    }

    const testResults = [];
    let reportedOutputBytes = 0;
    for (let index = 0; index < cases.length; index += 1) {
      if (this.cancelRequested) throw new Error('The C execution was cancelled.');
      const testCase = cases[index];
      onStatus({ phase: 'running', current: index + 1, total: cases.length });

      const remainingOutputBytes = Math.max(
        0,
        MAX_SUBMISSION_OUTPUT_BYTES - SUBMISSION_DIAGNOSTICS_RESERVE_BYTES - reportedOutputBytes,
      );
      const result = await this.#executeCase(compilation.wasmBytes, testCase, remainingOutputBytes);
      testResults.push(result);
      reportedOutputBytes += getUtf8ByteLength(result.stdout) + getUtf8ByteLength(result.stderr);
    }

    return {
      runner_type: this.type,
      runner_version: this.version,
      compiler_version: this.compilerVersion,
      compilation: {
        status: 'success',
        duration_ms: compilation.durationMs,
        diagnostics: compilation.diagnostics,
      },
      test_results: testResults,
    };
  }

  cancel() {
    this.cancelRequested = true;
    this.#stopCompilerWorker(new Error('The C execution was cancelled.'));
    this.activeWorkers.forEach((worker) => {
      if (typeof worker.cancelRun === 'function') worker.cancelRun();
      else worker.terminate();
    });
    this.activeWorkers.clear();
  }

  dispose() {
    this.cancel();
  }

  #compile(sourceCode, onStatus) {
    if (this.pendingCompile) {
      return Promise.reject(new Error('This runner is already compiling another submission.'));
    }

    const worker = this.#ensureCompilerWorker();
    onStatus({ phase: 'loading-toolchain' });

    return new Promise((resolve, reject) => {
      const pending = { resolve, reject, onStatus, timer: null };
      this.pendingCompile = pending;
      pending.timer = window.setTimeout(() => {
        this.#stopCompilerWorker(new Error(
          `The C compiler did not finish loading and compiling within ${Math.round(this.compileTimeoutMs / 1000)} seconds.`,
        ));
      }, this.compileTimeoutMs);

      try {
        worker.postMessage({
          type: 'compile',
          sourceCode,
          assetBaseUrl: assetBaseUrl(),
          maxDiagnosticsBytes: MAX_COMPILER_DIAGNOSTICS_BYTES,
        });
      } catch (error) {
        this.#stopCompilerWorker(error instanceof Error ? error : new Error(String(error)));
      }
    });
  }

  #ensureCompilerWorker() {
    if (this.compilerWorker) return this.compilerWorker;

    const worker = new Worker(compilerWorkerUrl, { type: 'module', name: 'assessment-wasm-compiler' });
    this.compilerWorker = worker;
    this.activeWorkers.add(worker);

    worker.onmessage = ({ data }) => {
      const pending = this.pendingCompile;
      if (!pending) return;

      if (data?.type === 'status') {
        pending.onStatus({ phase: data.message || 'compiling' });
        return;
      }
      if (data?.type === 'progress') {
        pending.onStatus({ phase: 'loading-toolchain', progress: data.value });
        return;
      }
      if (data?.type !== 'compile-result') return;

      window.clearTimeout(pending.timer);
      this.pendingCompile = null;
      pending.resolve({
        status: data.ok ? 'success' : 'error',
        durationMs: data.durationMs || 0,
        diagnostics: data.diagnostics || '',
        wasmBytes: data.wasmBytes,
      });
    };

    worker.onerror = (event) => {
      this.#stopCompilerWorker(new Error(event.message || 'The browser C compiler failed to start.'));
    };

    return worker;
  }

  #stopCompilerWorker(error) {
    const worker = this.compilerWorker;
    const pending = this.pendingCompile;
    this.pendingCompile = null;
    if (pending) window.clearTimeout(pending.timer);

    if (worker) {
      worker.terminate();
      this.activeWorkers.delete(worker);
      this.compilerWorker = null;
    }

    if (pending) pending.reject(error);
  }

  #executeCase(wasmBytes, testCase, remainingOutputBytes) {
    const worker = new Worker(testcaseWorkerUrl, { type: 'module', name: `assessment-wasm-case-${testCase.id}` });
    this.activeWorkers.add(worker);

    return new Promise((resolve, reject) => {
      const startedAt = performance.now();
      const output = { stdout: '', stderr: '' };
      let settled = false;

      const cleanup = () => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        worker.terminate();
        this.activeWorkers.delete(worker);
        delete worker.cancelRun;
      };

      const finish = (result) => {
        cleanup();
        resolve({
          test_case_id: testCase.id,
          status: result.status,
          exit_code: result.exitCode ?? null,
          duration_ms: result.durationMs ?? Math.round(performance.now() - startedAt),
          stdout: result.stdout ?? output.stdout,
          stderr: result.stderr ?? output.stderr,
        });
      };

      const timer = window.setTimeout(() => finish({
        status: CASE_STATUS.TIME_LIMIT_EXCEEDED,
        stderr: `Execution exceeded the ${testCase.timeLimitSeconds} second time limit.`,
      }), testCase.timeLimitSeconds * 1000);

      worker.cancelRun = () => {
        cleanup();
        reject(new Error('The C execution was cancelled.'));
      };

      worker.onmessage = ({ data }) => {
        if (data?.type === 'output' && (data.stream === 'stdout' || data.stream === 'stderr')) {
          output[data.stream] += data.text || '';
          return;
        }
        if (data?.type === 'output-limit') {
          finish({
            status: CASE_STATUS.RUNTIME_ERROR,
            stderr: `Program output exceeded the ${MAX_CASE_OUTPUT_BYTES / 1024} KB per-stream or ${MAX_COMBINED_OUTPUT_BYTES / 1024} KB combined limit.`,
          });
          return;
        }
        if (data?.type === 'execution-result') finish(data);
      };

      worker.onerror = (event) => finish({
        status: CASE_STATUS.RUNTIME_ERROR,
        stderr: event.message || 'The program stopped unexpectedly.',
      });

      const transferableBytes = wasmBytes.slice(0);
      worker.postMessage({
        type: 'execute',
        wasmBytes: transferableBytes,
        input: testCase.input,
        maxStreamBytes: MAX_CASE_OUTPUT_BYTES,
        maxCombinedBytes: Math.min(MAX_COMBINED_OUTPUT_BYTES, remainingOutputBytes),
      }, [transferableBytes]);
    });
  }
}

export const createWasmRunner = (options) => new WasmRunner(options);

export default WasmRunner;
