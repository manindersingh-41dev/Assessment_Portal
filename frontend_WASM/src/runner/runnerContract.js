export const RUNNER_TYPE = Object.freeze({
  WEB_WASM: 'web_wasm',
  DESKTOP_GCC: 'desktop_gcc',
});

export const CASE_STATUS = Object.freeze({
  COMPLETED: 'completed',
  RUNTIME_ERROR: 'runtime_error',
  TIME_LIMIT_EXCEEDED: 'time_limit_exceeded',
  MEMORY_LIMIT_EXCEEDED: 'memory_limit_exceeded',
});

export const MAX_SOURCE_BYTES = 100_000;
export const MAX_CASE_OUTPUT_BYTES = 64 * 1024;
export const MAX_COMBINED_OUTPUT_BYTES = 128 * 1024;
export const MAX_SUBMISSION_OUTPUT_BYTES = 1_000_000;
export const SUBMISSION_DIAGNOSTICS_RESERVE_BYTES = 64 * 1024;
export const MAX_COMPILER_DIAGNOSTICS_BYTES = 20_000;
export const MAX_CASE_SNAPSHOT_BYTES = 2 * 1024 * 1024;
export const MAX_TEST_CASES = 250;
// The first compile includes downloading and initializing the roughly 29 MB toolchain.
export const DEFAULT_COMPILE_TIMEOUT_MS = 120_000;
export const WASM_RUNNER_VERSION = '1.0.0';
export const WASM_COMPILER_VERSION = 'Clang 22.1.8 (WASI Preview 1)';

export const getUtf8ByteLength = (value) => new TextEncoder().encode(value || '').byteLength;

export const validateSourceCode = (sourceCode) => {
  if (typeof sourceCode !== 'string' || sourceCode.length === 0) {
    throw new Error('Enter C source code before running this question.');
  }

  if (getUtf8ByteLength(sourceCode) > MAX_SOURCE_BYTES) {
    throw new Error('Source code must be 100 KB or smaller.');
  }
};

export const normalizeTestCases = (testCases, defaultTimeLimitSeconds = 10) => {
  if (!Array.isArray(testCases) || testCases.length === 0) {
    throw new Error('No test cases were provided for this run.');
  }
  if (testCases.length > MAX_TEST_CASES) {
    throw new Error(`A question cannot run more than ${MAX_TEST_CASES} test cases.`);
  }

  let totalInputBytes = 0;
  return testCases.map((testCase, index) => {
    if (!testCase?.id) throw new Error(`Test case ${index + 1} is missing its identifier.`);
    const input = typeof testCase.input === 'string' ? testCase.input : '';
    totalInputBytes += getUtf8ByteLength(input);
    if (totalInputBytes > MAX_CASE_SNAPSHOT_BYTES) {
      throw new Error(`Test case inputs exceed the ${MAX_CASE_SNAPSHOT_BYTES / (1024 * 1024)} MB execution limit.`);
    }

    return {
      id: String(testCase.id),
      input,
      timeLimitSeconds: Math.max(1, Number(
        testCase.time_limit_seconds || testCase.timeLimitSeconds || defaultTimeLimitSeconds || 10,
      )),
    };
  });
};
