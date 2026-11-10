import { DESKTOP_RUNNER_VERSION } from '../runnerContract';

const getInvoke = () => {
  const invoke = window?.__TAURI__?.core?.invoke;
  if (typeof invoke !== 'function') {
    throw new Error('The native desktop C runner is available only in the Windows application.');
  }
  return invoke;
};

const createRunId = () => window.crypto?.randomUUID?.()
  || `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export const detectDesktopCompiler = () => getInvoke()('detect_gcc');

export class DesktopGccRunner {
  constructor() {
    this.type = 'desktop_gcc';
    this.version = DESKTOP_RUNNER_VERSION;
    this.compilerVersion = '';
    this.runId = createRunId();
    this.cancelRequested = false;
  }

  async runSubmission({ sourceCode, testCases, timeLimitSeconds = 10, onStatus = () => {} }) {
    this.cancelRequested = false;
    onStatus({ phase: 'Preparing the local GCC compiler…' });
    const compilerVersion = await detectDesktopCompiler();
    if (this.cancelRequested) throw new Error('The C execution was cancelled.');
    this.compilerVersion = compilerVersion;
    onStatus({ phase: 'Compiling the submitted C code…' });

    const result = await getInvoke()('run_c_submission', {
      runId: this.runId,
      sourceCode,
      testCases: testCases.map((testCase) => ({
        id: String(testCase.id),
        input: typeof testCase.input === 'string' ? testCase.input : '',
        time_limit_seconds: testCase.time_limit_seconds || testCase.timeLimitSeconds || timeLimitSeconds,
      })),
      timeLimitSeconds,
    });

    return result;
  }

  cancel() {
    this.cancelRequested = true;
    getInvoke()('cancel_c_submission', { runId: this.runId }).catch(() => {});
  }

  dispose() {
    this.cancel();
  }
}

export const createDesktopGccRunner = () => new DesktopGccRunner();
