# Approach 1 Frontend Status

Updated: 2026-11-09

The browser execution implementation and frontend integration are complete. Approach 1 is not ready for production rollout until the deployment and live API checks below are completed.

## Implemented

- C compiles in a browser worker using the pinned Clang 22.1.8 WASI toolchain. The toolchain is loaded only when a student runs or submits code.
- Each submission compiles once, then runs its cases in separate workers with per-case time limits and output caps.
- Sample run requests and executes visible cases only. It shows expected and actual output locally.
- Submit creates the pending server record before compiling, runs all cases, then reports outputs for server-side comparison and scoring.
- The attempt page displays backend results, including visible outputs and status-only hidden results. The backend API remains responsible for expected outputs, verdicts, marks and privacy.
- Pending browser evaluations continue while the student changes questions. Another question can be submitted while a prior evaluation runs; runner execution is serialized in the browser. Pending evaluations can be resumed after a navigation or reload.
- Unsupported browsers and request/compiler errors are shown in the question result area.
- Draft autosave, assessment timers, and the resizable editor/results panel remain part of the attempt page.

## Verification completed

- Browser feasibility corpus: **18/18 passed** in the local browser, covering C input/output, standard library use, math functions, compiler errors, infinite-loop termination and output caps.
- Production Vite build: passed after copying the Monaco and WASM runtime assets.
- Oxlint: no errors. Four warnings remain in pre-existing faculty/dashboard files about synchronous state updates in effects.
- The generated production build is about 55 MB, including about 28 MB of compressed compiler/runtime assets. Generated `dist` and `public/clang` files are ignored; the prebuild scripts recreate them.

## Remaining before go-live

1. Choose the deployment host and configure it to serve `/clang/` with caching and revalidation appropriate for these stable asset paths. Serve the site over HTTPS.
2. Configure `VITE_API_URL`, backend CORS/allowed origins if frontend and API use different origins, and production API authentication.
3. Apply backend migrations `0006` and `0007` in the target database before enabling the client-evaluation endpoints.
4. Run an authenticated end-to-end assessment with the deployed frontend and backend. Check visible/hidden result privacy, latest-submission scoring, network retry/resume, timer expiry and assignment scorecards.
5. Pilot with faculty and students, then check API/database response times with the expected 50–100 concurrent students.

These rollout checks need a selected host and a running target backend/database; the local frontend build and browser runner corpus do not validate production hosting or authenticated API behavior.
