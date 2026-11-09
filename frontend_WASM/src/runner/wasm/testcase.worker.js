import {
  ConsoleStdout,
  File,
  OpenFile,
  WASI,
  WASIProcExit,
} from '@bjorn3/browser_wasi_shim';

const encoder = new TextEncoder();

const isMemoryFailure = (error) => /out of bounds|memory access|cannot enlarge memory|allocation failed/i
  .test(`${error?.name || ''} ${error?.message || ''}`);

const makeOutputFd = (stream, request, counters) => new ConsoleStdout((chunk) => {
  const remainingForStream = request.maxStreamBytes - counters[stream].bytes;
  const remainingCombined = request.maxCombinedBytes - counters.stdout.bytes - counters.stderr.bytes;
  const allowedBytes = Math.max(0, Math.min(remainingForStream, remainingCombined));
  const capturedBytes = chunk.subarray(0, allowedBytes);

  counters[stream].bytes += capturedBytes.byteLength;
  const text = counters[stream].decoder.decode(capturedBytes, { stream: true });
  counters[stream].text += text;
  if (capturedBytes.byteLength) {
    self.postMessage({ type: 'output', stream, text });
  }

  if (capturedBytes.byteLength < chunk.byteLength && !counters.outputLimitReached) {
    counters.outputLimitReached = true;
    self.postMessage({ type: 'output-limit' });
  }
});

self.onmessage = async (event) => {
  const request = event.data;
  if (!request || request.type !== 'execute') return;

  const startedAt = performance.now();
  const counters = {
    stdout: { bytes: 0, text: '', decoder: new TextDecoder() },
    stderr: { bytes: 0, text: '', decoder: new TextDecoder() },
    outputLimitReached: false,
  };

  try {
    const module = await WebAssembly.compile(request.wasmBytes);
    const fds = [
      new OpenFile(new File(encoder.encode(request.input || ''))),
      makeOutputFd('stdout', request, counters),
      makeOutputFd('stderr', request, counters),
    ];
    const wasi = new WASI([], [], fds);
    const instance = await WebAssembly.instantiate(module, {
      wasi_snapshot_preview1: wasi.wasiImport,
    });

    let exitCode = 0;
    try {
      const result = wasi.start(instance);
      if (Number.isInteger(result)) exitCode = result;
    } catch (error) {
      if (error instanceof WASIProcExit || error?.name === 'WASIProcExit') {
        exitCode = Number(error.code ?? error.exitCode ?? 1);
      } else {
        throw error;
      }
    }

    if (counters.outputLimitReached) return;

    postResult({
      status: exitCode === 0 ? 'completed' : 'runtime_error',
      exitCode,
      stdout: counters.stdout.text,
      stderr: counters.stderr.text,
      durationMs: Math.round(performance.now() - startedAt),
    });
  } catch (error) {
    postResult({
      status: isMemoryFailure(error) ? 'memory_limit_exceeded' : 'runtime_error',
      exitCode: null,
      stdout: counters.stdout.text,
      stderr: counters.stderr.text,
      error: String(error?.message || error),
      durationMs: Math.round(performance.now() - startedAt),
    });
  }
};

function postResult(result) {
  self.postMessage({ type: 'execution-result', ...result });
}
