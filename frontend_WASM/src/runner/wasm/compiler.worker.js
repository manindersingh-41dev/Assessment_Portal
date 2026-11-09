import { compilerDiagnostics } from '@live-codes/clang-wasm/toolchain';
import {
  BrowserClangRuntime,
  loadRuntimeManifest,
  resolveRuntimeManifestUrl,
} from '@wasm-idle/llvm-core/clang';

const ANSI_ESCAPE = new RegExp(`${String.fromCharCode(27)}\\[[0-?]*[ -/]*[@-~]`, 'g');
const formatCompilerDiagnostics = (raw) => {
  const plainText = raw.replace(ANSI_ESCAPE, '');
  try {
    return compilerDiagnostics(plainText).join('\n') || plainText;
  } catch {
    return plainText;
  }
};
const truncateUtf8 = (text, maxBytes) => {
  const bytes = new TextEncoder().encode(text);
  let end = Math.min(bytes.byteLength, maxBytes);
  const strictDecoder = new TextDecoder('utf-8', { fatal: true });
  while (end > 0) {
    try {
      strictDecoder.decode(bytes.subarray(0, end));
      break;
    } catch {
      end -= 1;
    }
  }
  return new TextDecoder().decode(bytes.subarray(0, end));
};

const post = (message, transfer = []) => self.postMessage(message, transfer);
let runtimePromise;
let compilerOutput = [];

const getRuntime = (request) => {
  if (!runtimePromise) {
    globalThis.SharedArrayBuffer ??= class SharedArrayBufferStub {};

    runtimePromise = (async () => {
      const manifest = await loadRuntimeManifest(resolveRuntimeManifestUrl(request.assetBaseUrl));
      const runtime = new BrowserClangRuntime({
        runtimeBaseUrl: request.assetBaseUrl,
        manifest,
        stdin: () => '',
        stdout: (chunk) => compilerOutput.push(chunk),
        progress: (value) => post({ type: 'progress', value }),
        log: true,
      });
      await runtime.ready;
      return runtime;
    })().catch((error) => {
      runtimePromise = undefined;
      throw error;
    });
  }

  return runtimePromise;
};

self.onmessage = async (event) => {
  const request = event.data;
  if (!request || request.type !== 'compile') return;

  compilerOutput = [];
  const startedAt = performance.now();

  try {
    post({
      type: 'status',
      message: runtimePromise ? 'Preparing the compiler…' : 'Loading the browser C compiler…',
    });
    const runtime = await getRuntime(request);

    post({ type: 'status', message: 'Compiling the submitted C code…' });

    let artifact;
    try {
      artifact = await runtime.compileArtifact(
        request.sourceCode,
        {
          language: 'C',
          fileName: 'main.c',
          compileArgs: ['-std=c11', '-O0', '-Wall', '-Wextra'],
        },
      );
    } catch (error) {
      const raw = [...compilerOutput, error?.message || String(error)].join('\n');
      post({
        type: 'compile-result',
        ok: false,
        diagnostics: truncateUtf8(formatCompilerDiagnostics(raw), request.maxDiagnosticsBytes),
        durationMs: Math.round(performance.now() - startedAt),
      });
      return;
    }

    const rawDiagnostics = compilerOutput.join('\n');
    const diagnostics = truncateUtf8(formatCompilerDiagnostics(rawDiagnostics), request.maxDiagnosticsBytes);

    const bytes = artifact?.bytes;
    if (!(bytes instanceof Uint8Array) || bytes.byteLength === 0) {
      throw new Error('The compiler did not return a runnable WebAssembly program.');
    }

    const transferableBytes = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    post({
      type: 'compile-result',
      ok: true,
      wasmBytes: transferableBytes,
      diagnostics,
      durationMs: Math.round(performance.now() - startedAt),
    }, [transferableBytes]);
  } catch (error) {
    const raw = [...compilerOutput, error?.message || String(error)].join('\n');
    post({
      type: 'compile-result',
      ok: false,
      diagnostics: truncateUtf8(raw.replace(ANSI_ESCAPE, ''), request.maxDiagnosticsBytes),
      durationMs: Math.round(performance.now() - startedAt),
    });
  }
};
