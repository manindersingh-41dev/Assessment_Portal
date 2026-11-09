# Frontend (WASM)

React/Vite client for the Geeta University Coding Assessment Portal. Student C submissions compile and run in browser workers using the pinned Clang/WASI packages. The backend API stores submission snapshots and remains responsible for result validation and scoring.

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
