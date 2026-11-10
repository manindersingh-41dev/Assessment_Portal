# Geeta Assessment Portal client

React/Vite client for the Geeta University Coding Assessment Portal. In a normal browser, C runs in workers using the pinned Clang/WASI packages. In the Tauri Windows app, C uses the desktop GCC runner. The backend API stores submission snapshots and remains responsible for result validation and scoring.

## Local setup

```bash
npm ci
cp .env.example .env
npm run dev
```

Set `VITE_API_URL` in `.env` to the backend API URL. The `predev` and `prebuild` scripts copy the Monaco editor and WASM runtime assets from installed packages.

## Useful commands

- `npm run build` — create a production build.
- `npm run lint` — run Oxlint.
- `npm run preview` — preview the production build locally.

See [`APPROACH1_FRONTEND_STATUS.md`](APPROACH1_FRONTEND_STATUS.md) for implementation status and remaining rollout checks, and [`WASM_FEASIBILITY_SPIKE.md`](WASM_FEASIBILITY_SPIKE.md) for the runner design and constraints.

## Windows desktop client (Approach 2)

The Tauri 2 shell is under `src-tauri/` and reuses this React app. Install Rust with the `stable-msvc` toolchain, Microsoft C++ Build Tools with **Desktop development with C++**, WebView2, and the Tauri CLI (`cargo install tauri-cli --version "^2.0.0" --locked`). Install GCC on the Windows laptop and add `gcc.exe` to `PATH`, or set `GEETA_GCC_PATH` to its full path. Set `VITE_API_URL` to the deployed HTTPS API before running `npm run desktop:build`; the preflight rejects an unset or non-HTTPS API URL. Read [`APPROACH2_WINDOWS_STATUS.md`](APPROACH2_WINDOWS_STATUS.md) and [`WORKLOG.md`](WORKLOG.md) for current status and work history.

Debian 13 can cross-build the Windows NSIS installer. Install Node/npm, Rust, `nsis`, `lld`, `llvm`, and `clang`; add the Rust target with `rustup target add x86_64-pc-windows-msvc`; install the tools with `cargo install --locked cargo-xwin` and `cargo install tauri-cli --version "^2.0.0" --locked`; then run `npm ci` and `npm run desktop:build:windows`. Tauri documents this cross-build route as less tested than building on Windows. The installer is written under `src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis/`. GCC still needs to be installed on the destination Windows laptop.
