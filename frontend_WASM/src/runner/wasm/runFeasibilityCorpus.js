import corpus from './feasibility-corpus.json';
import { createWasmRunner } from './WasmRunner.js';

const evaluateCase = (testCase, result) => {
  if (testCase.expect_compile_error) {
    return {
      passed: result.compilation.status === 'error' && Boolean(result.compilation.diagnostics),
      actual: result.compilation.diagnostics,
    };
  }

  const execution = result.test_results[0];
  if (testCase.expect_timeout) {
    return {
      passed: execution?.status === 'time_limit_exceeded',
      actual: execution?.status || 'missing execution result',
    };
  }

  if (testCase.expect_output_limit) {
    return {
      passed: execution?.status === 'runtime_error' && execution.stderr.includes('Program output exceeded'),
      actual: execution?.status === 'runtime_error' ? execution.stderr : execution?.status || 'missing execution result',
    };
  }

  const passed = result.compilation.status === 'success'
    && execution?.status === 'completed'
    && execution.stdout === testCase.expected_stdout;
  return {
    passed,
    actual: execution?.stdout ?? result.compilation.diagnostics,
  };
};

export const runFeasibilityCorpus = async ({
  runner = createWasmRunner(),
  onStatus = () => {},
  onCaseResult = () => {},
  timeLimitSeconds = 1,
} = {}) => {
  const results = [];

  try {
    for (const testCase of corpus) {
      const result = await runner.runSubmission({
        sourceCode: testCase.source,
        testCases: [{
          id: testCase.id,
          input: testCase.input,
          time_limit_seconds: timeLimitSeconds,
        }],
        timeLimitSeconds,
        onStatus: (status) => onStatus({ ...status, testCaseId: testCase.id }),
      });
      const evaluation = evaluateCase(testCase, result);
      const summary = {
        id: testCase.id,
        category: testCase.category,
        passed: evaluation.passed,
        actual: evaluation.actual,
      };
      results.push(summary);
      onCaseResult(summary);
    }

    return {
      passed: results.filter((result) => result.passed).length,
      total: results.length,
      results,
    };
  } finally {
    runner.dispose();
  }
};

export default runFeasibilityCorpus;
