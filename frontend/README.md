# Psychogram frontend

Production-oriented React + TypeScript SPA for the Psychogram FastAPI API. Runtime demo/fake data is deliberately absent: every domain screen reads or writes `/api/v1`.

## Run

```powershell
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

FastAPI should run on `http://127.0.0.1:8000`. Vite proxies `/api` during development; set `VITE_API_ORIGIN` when the API has a different public origin.

Pilot feature flags (default `false`): `VITE_ENABLE_REGISTRATION` shows self-service sign-up and `VITE_ENABLE_CSV_IMPORT` shows CSV import. Each must match its backend flag (`PSYCHOGRAM_REGISTRATION_ENABLED`, `PSYCHOGRAM_CSV_IMPORT_ENABLED`); the backend refuses the request either way.

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test
npm.cmd run build
```

## Security and deployment

The bearer token is kept in `sessionStorage`, not persistent `localStorage`. A production deployment should prefer an audited same-site BFF/session wrapper where available. PII is fetched only after an explicit reveal action and only when `/auth/me` grants `can_view_pii`; tenant switching clears reveal state.

Serve the SPA with history fallback to `index.html`, HTTPS, and at least this CSP (replace `<API_ORIGIN>`):

```text
default-src 'self'; img-src 'self' data: https://api.iconify.design; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self' <API_ORIGIN>; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'
```

Icons use only the official Iconify Lucide SVG API through `<img>`, with fixed dimensions, `no-referrer`, anonymous CORS and a local text fallback. No remote script runs. Remote requests may disclose the client IP and icon name to Iconify; review this during privacy release approval.

Official exports are JSON and CSV only. The UI intentionally has no pause/archive/member-edit/XLSX/PDF/template-download controls because the matching backend contracts (B07–B10/B12) do not exist.
