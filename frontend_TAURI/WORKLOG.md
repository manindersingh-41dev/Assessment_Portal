# Tauri application work log

This log records implementation work performed in `frontend_TAURI/`. The separate `frontend_WASM/` application is out of scope and must remain unchanged.

## 2026-11-10

- Resumed Approach 2 in the user-created `frontend_TAURI/` copy.
- Inspected the copied React/Vite UI, Tauri shell, GCC runner bridge, and current Git state. The parent repository reports only `frontend_TAURI/` as untracked; no other working-tree changes were present at inspection time.
- Confirmed Node dependencies and GCC are available locally. Rust/Cargo are not available, so native compilation and Windows packaging cannot be performed on this host yet.
- Added a local `.gitignore` for generated bundles, copied Clang/Monaco assets, Cargo output, generated Tauri schemas, and environment files. Existing local assets remain in place and can be recreated by the frontend prebuild scripts.
- Added a local Approach 2 status document and updated this app's README to reference it, keeping documentation inside the new app folder.
- Added the app-local `.env.example`, corrected the application title, and documented the packaged Windows CORS origin requirement (`http://tauri.localhost`). The backend's current default CORS list only covers Vite development origins.
- Fixed the two `unicorn(no-useless-fallback-in-spread)` lint warnings in the assessment page's local draft merge.
- Tightened Windows Job Object memory limits to 512 MB per process and per job. The process launcher now preserves the Windows resume error before closing its handle, terminates leftover child processes, and joins output readers before returning results.
- Added production and development CSP policies. Production network connections are limited to app IPC and HTTPS; development also allows local Vite HMR and API endpoints.
- Added a desktop packaging preflight that requires an absolute HTTPS `VITE_API_URL`, so a release cannot silently use the localhost default.
- Added a Tauri resource mapping and compiler lookup for a bundled GCC distribution. Release packaging now also checks for `resources/gcc/bin/gcc.exe`; development continues to support `GEETA_GCC_PATH` or `PATH`.
- Added a `resources/gcc/README.md` describing the expected distribution layout, license notices, and version/checksum record. The binary folder is ignored by Git until a compiler distribution is selected and reviewed.
- Reworded shared attempt-page fallback errors so Tauri GCC failures are described as local runner failures rather than browser failures.
- `npm run lint` passed with no warnings, `npm run build` passed with separate compiler and testcase worker chunks, and the Tauri config JSON and HTTPS URL validation passed. The release preflight now also requires a staged Windows GCC binary, which is not available in this host environment.
- Rust/Cargo are still unavailable on this host, so the modified native runner has not been compiled and no Windows installer has been produced.
- Aligned release packaging with the requested installed-GCC model: the desktop app now resolves `GEETA_GCC_PATH` or `gcc.exe` from `PATH`, and the installer no longer requires or copies a bundled compiler. The HTTPS API preflight remains required.
- Frontend lint/build could not run in this execution environment because `npm` is not installed. Native Windows validation still requires the Windows build environment listed above.
- Configured `.env.production` for the user's Render backend and added a `desktop:build:windows` cross-build script using Tauri's documented `cargo-xwin` route. The current shell has Cargo/Rust but no Node/npm, NSIS, or LLVM cross-build tools, so no installer was generated.

## 2026-11-12

- Changed the Windows release build to stage MSYS2 UCRT64 into the app's Tauri resource bundle. The Windows-only staging preflight verifies GCC's headers, runtime library, C frontend, and a compiled program before packaging.
- Updated the Rust runner to resolve GCC from the bundled resource path and add its `bin` folder to the environment for compilation and execution. `GEETA_GCC_PATH` remains a developer override; development can fall back to `PATH`.
- Updated Windows packaging and rollout documentation. The compiler payload remains ignored by Git and is generated from the build computer's MSYS2 installation.
- Static JSON and whitespace checks pass. This Debian environment has no Node.js and no configured Rust toolchain, so the Windows staging smoke check and installer build could not run here.

## Next

- Build the Windows installer with MSYS2 UCRT64 installed; the build stages and bundles GCC and runs a smoke check on Windows.
- Install the resulting app on a clean Windows laptop and verify C compile/run works without a separate GCC installation.
- Add and validate a Windows access-control sandbox before student release; Job Objects currently limit resources and processes but do not block file or network access.
- Confirm the deployed backend allows `http://tauri.localhost` in CORS, then build and smoke-test the NSIS installer with its production API URL.
- Continue app-specific work in this folder and append a dated entry after each meaningful change or check.
