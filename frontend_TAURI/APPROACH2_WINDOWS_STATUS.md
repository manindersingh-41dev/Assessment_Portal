# Approach 2: Windows desktop client

**Status:** Development scaffold in `frontend_TAURI/`. This folder contains the separate Tauri application. The app reuses the V2 React portal and submits C evaluations through the runner-neutral backend API as `desktop_gcc`.

## Current implementation

- Tauri 2 shell configured to package the Vite app as a Windows NSIS installer, with a restrictive production CSP and a development CSP for local Vite/API connections.
- Rust commands use `GEETA_GCC_PATH` as an optional developer override, then resolve the GCC compiler bundled under Tauri's resource directory, and finally fall back to `PATH` for development. GCC's `bin` directory is added to compiler and student-program `PATH` so its runtime DLLs are available. C runs use fixed C11 flags, a temporary working directory, per-case timeouts, byte-limited stdout/stderr, cancellation, and Windows Job Objects for process-tree cleanup, active-process limits, and per-process plus total job memory limits.
- React runner selection uses local GCC inside Tauri and browser WASM outside Tauri.
- Sample runs remain local and use only visible test cases. Final submissions use the shared client-evaluation API and preserve runner metadata with retry state.
- The Tauri production build now refuses to package when `VITE_API_URL` is missing or is not HTTPS. Configure it in `.env.production` or the build environment.

## Current environment limits

- Debian can cross-build the Windows NSIS installer with `cargo-xwin`, the Windows MSVC Rust target, NSIS, LLVM/LLD, and Clang. This execution environment has Rust/Cargo but lacks Node/npm and the cross-build tools, so the installer cannot be produced here yet.
- A packaged Windows Tauri 2 app uses `http://tauri.localhost`, while the backend's default CORS allow list covers local Vite origins. The deployed backend's `CORS_ALLOWED_ORIGINS` must include the Tauri origin. See [Tauri's Windows origin note](https://v2.tauri.app/start/migrate/from-tauri-1/).
- The release build stages the MSYS2 UCRT64 prefix from `GEETA_GCC_BUNDLE_SOURCE` (default `C:\msys64\ucrt64`) into `resources/gcc/ucrt64`, validates its compiler paths, and runs a compile-and-run smoke check on Windows before bundling it. The full prefix, including runtime DLLs and license files, is packaged into the NSIS installer; students do not install GCC separately. No compiler payload is tracked in Git.
- Windows Job Objects constrain memory/process count and terminate associated processes. They do not restrict file or network access. Native execution is not ready for student release until an access-control model is implemented and validated.
- The production CSP permits HTTPS API connections. The CSP and backend CORS check are separate; the deployed backend must allow the Tauri origin for API calls to succeed.
- No `Cargo.lock` is present. Generate it on a Rust-equipped build environment and retain it for reproducible builds.

## Build commands

On Windows, install Node.js 22.12+, Rust with the `stable-msvc` toolchain, Microsoft C++ Build Tools with **Desktop development with C++**, and the Tauri CLI (`cargo install tauri-cli --version "^2.0.0" --locked`). Install MSYS2 and, in its UCRT64 terminal, run `pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-binutils`. The release build automatically stages that compiler before bundling. For local development, put GCC on `PATH` or set `GEETA_GCC_PATH`. Then run:

```powershell
npm ci
$env:VITE_API_URL = "https://api.example.edu/api"
npm run desktop:dev
npm run desktop:build
```

Set `VITE_API_URL` to the deployed backend URL before `desktop:build`; the packaging preflight rejects an unset or non-HTTPS URL. The app checks GCC on the laptop when a C run starts.

On Debian 13, install Node/npm, Rust, `nsis`, `lld`, `llvm`, and `clang`; add `x86_64-pc-windows-msvc` with rustup; install `cargo-xwin` and the Tauri CLI; and make a Windows MSYS2 UCRT64 prefix available as `GEETA_GCC_BUNDLE_SOURCE`. Then run `npm ci` and `npm run desktop:build:windows`. Tauri's cross-build flow is less tested than building on Windows, and the GCC smoke check runs only on Windows. The unsigned installer can be installed on Windows, though Windows may show a publisher warning.

## Backend contract

Use `../backend/CLIENT_EXECUTION_API.md` as the source of truth for execution cases, idempotent submissions, result reporting, and hidden-case privacy. This app uses visible cases only for sample runs and does not send hidden expected output to the client.
