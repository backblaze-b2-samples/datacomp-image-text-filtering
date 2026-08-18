<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with run stats and recent runs
  - **Filter Runs** — the primary entity: create/read/edit/delete/run, per-shard metrics
  - **Pool Explorer** — scoped shard viewer for `pool/` + `filtered/` (thumbnail + caption + CLIP score + kept/dropped)
  - **Bucket Explorer** — full-bucket browse with preview, download, delete
  - **Ingest** — presigned direct-to-B2 upload of raw shards
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for Filter Runs, the Pool Explorer, files, and uploads
  - B2 S3 integration via boto3 (confined to `repo/`)
  - **DataComp CLIP filter engine** in `service/filtering.py` — lazy-imports the ML stack, auto-detects device, scores image-text alignment, writes filtered shards + metrics
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (runs.py, pool.py, files.py, ...)
    config/                Settings loaded from environment
    repo/                  B2 S3 client + runs_store (data access layer)
    service/               Business logic (runs, filtering, pool, files, upload)
    runtime/               FastAPI route handlers
  scripts/seed_pool.py     Synthetic keyless pool generator
  requirements-ml.txt      Heavy CLIP stack (excluded from setup + CI)
  tests/                   pytest tests (structural + integration)
```

The **ML stack boundary** mirrors the boto3 boundary: `torch` / `torchvision` /
`open_clip` / `webdataset` may be imported ONLY in `app/service/filtering.py`
(enforced by `tests/test_structure.py::test_ml_stack_only_in_filtering`). They
are lazy-imported inside functions and shipped in `requirements-ml.txt`, so the
base venv boots and every static gate passes without them.

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. Each service's versioned config sits at its own root —
  `railway.json` and `services/api/railway.json` — the default path Railway
  discovers, so a one-click template deploy inherits the same build, start, and
  health behavior with nothing to configure by hand. The human-approved
  staging/production contract lives in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store (no database). One bucket holds, by prefix:
  - `pool/` — raw input WebDataset `.tar` shards
  - `filtered/<run_id>/` — filtered output shards
  - `metrics/<run_id>/` — per-shard quality metrics JSON
  - `runs/<id>/manifest.json` — the Filter Run entity (config + status + stats)
  - `uploads/` — objects added via the Ingest page
  - S3 ops: `list_objects_v2`, `get_object`, `put_object`, `head_object`, `delete_object(s)`, `generate_presigned_url`
- The regional S3 endpoint is built at runtime from `B2_REGION` (`https://s3.<B2_REGION>.backblazeb2.com`); no region is hardcoded.

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Filter Run**: Browser -> `POST /runs` (create pending manifest) -> `POST /runs/{id}/run` (marks running, schedules a FastAPI BackgroundTask) -> `service/filtering.run_filter` streams `pool/` shards from B2, CLIP-scores every pair, applies the strategy, writes `filtered/<id>/*.tar` + `metrics/<id>/*.json` back to B2, updates the manifest to `completed`. The UI polls `GET /runs/{id}` every 2s while running. A missing ML stack or empty pool persists `failed` — the POST never 500s.
- **Pool Explorer**: Browser -> `GET /pool/shards?scope=pool|filtered` (list shards) -> `GET /pool/shard?key=...` -> service reads the shard from B2, returns image-text pairs (thumbnails as data URLs; scores/kept from the run's metrics JSON for filtered shards).
- **Ingest (upload)**: Browser -> `POST /upload/presign` -> Browser PUTs bytes **directly to B2** -> `POST /upload/verify` (API HEADs + Range-sniffs the stored object).
- **List / Download / Delete** (Bucket Explorer): `GET /files`, `GET /files/{key}/download` (presigned), `DELETE /files/{key}`.

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- CLIP filter engine (ML stack lives here only): `services/api/app/service/filtering.py`
- Pure filter helpers (no ML): `services/api/app/service/filter_ops.py`
- Filter Run orchestration: `services/api/app/service/runs.py`
- Run manifest store (B2, repo layer): `services/api/app/repo/runs_store.py`
- Pool Explorer service: `services/api/app/service/pool.py`
- Run/pool route handlers: `services/api/app/runtime/runs.py`, `services/api/app/runtime/pool.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`runs.py`, `pool.py`, `files.py`, `upload.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Seed script: `services/api/scripts/seed_pool.py`
- Structural tests: `services/api/tests/test_structure.py`
- OpenAPI contract: `docs/api/openapi.json`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Filter Runs](docs/features/filter-runs.md)
- [Pool Explorer](docs/features/pool-explorer.md)
- [File Upload (Ingest)](docs/features/file-upload.md)
- [Bucket Explorer](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
