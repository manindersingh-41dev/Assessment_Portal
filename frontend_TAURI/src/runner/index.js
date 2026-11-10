import { createDesktopGccRunner, detectDesktopCompiler } from './desktop/DesktopGccRunner';
import { createWasmRunner } from './wasm/WasmRunner';
import {
  DESKTOP_RUNNER_VERSION,
  RUNNER_TYPE,
  WASM_COMPILER_VERSION,
  WASM_RUNNER_VERSION,
} from './runnerContract';

export {
  CASE_STATUS,
  DESKTOP_RUNNER_VERSION,
  RUNNER_TYPE,
  WASM_COMPILER_VERSION,
  WASM_RUNNER_VERSION,
} from './runnerContract';
export { createWasmRunner, WasmRunner } from './wasm/WasmRunner';
export { createDesktopGccRunner, detectDesktopCompiler, DesktopGccRunner } from './desktop/DesktopGccRunner';

export const isDesktopApp = () => typeof window !== 'undefined'
  && typeof window.__TAURI__?.core?.invoke === 'function';

export const supportsRunner = () => isDesktopApp()
  || (typeof Worker !== 'undefined'
    && typeof WebAssembly !== 'undefined'
    && typeof WebAssembly.compile === 'function');

export const createRunner = () => {
  if (isDesktopApp()) return createDesktopGccRunner();
  return createWasmRunner();
};

export const getRunnerProfile = async () => {
  if (isDesktopApp()) {
    return {
      runner_type: RUNNER_TYPE.DESKTOP_GCC,
      runner_version: DESKTOP_RUNNER_VERSION,
      compiler_version: await detectDesktopCompiler(),
    };
  }
  return {
    runner_type: RUNNER_TYPE.WEB_WASM,
    runner_version: WASM_RUNNER_VERSION,
    compiler_version: WASM_COMPILER_VERSION,
  };
};
