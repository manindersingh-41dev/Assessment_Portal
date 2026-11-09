# Geeta University Coding Assessment Portal — V2

V2 is the active codebase for the assessment portal. `Portal_V1` is separate and is not part of this repository.

## Components

- `backend/` — Django REST API, authentication, assessments, submissions, and result storage.
- `frontend_WASM/` — React/Vite portal. Student C code runs in the browser through the pinned WASM toolchain; the backend stores submissions and calculates the official result.

The backend keeps both the client-evaluation API and the legacy server-execution path so the two planned execution approaches can share the same assessment data and API. The old Docker Compose deployment bundle has been removed; it was not the Render native-Python deployment configuration.

## Local development

### Backend

See [`backend/SETUP.md`](backend/SETUP.md). In short: install `backend/requirements.txt`, configure `backend/.env` with a local PostgreSQL `DATABASE_URL` and the required email settings, run migrations, then start Django on port 8000.

### Frontend

```bash
cd frontend_WASM
npm ci
cp .env.example .env
npm run dev
```

Set `VITE_API_URL` in `.env` to the backend API URL. The Vite pre-start and pre-build scripts copy the Monaco and WASM runtime assets from installed packages.

## Project documentation

- [`backend/CLIENT_EXECUTION_API.md`](backend/CLIENT_EXECUTION_API.md) — client-evaluation API and legacy transition behavior.
- [`backend/ASSESSMENTS_API.md`](backend/ASSESSMENTS_API.md), [`backend/QUESTIONS_API.md`](backend/QUESTIONS_API.md), [`backend/SUBMISSIONS_API.md`](backend/SUBMISSIONS_API.md), [`backend/RESULTS_API.md`](backend/RESULTS_API.md), and [`backend/AUTH_API.md`](backend/AUTH_API.md) — API references.
- [`frontend_WASM/APPROACH1_FRONTEND_STATUS.md`](frontend_WASM/APPROACH1_FRONTEND_STATUS.md) — current frontend implementation and rollout checks.
- [`frontend_WASM/WASM_FEASIBILITY_SPIKE.md`](frontend_WASM/WASM_FEASIBILITY_SPIKE.md) — WASM runner design and constraints.

Keep `.env` files, local databases, virtual environments, `node_modules`, generated WASM assets, and build output out of Git; the repository `.gitignore` excludes them.
