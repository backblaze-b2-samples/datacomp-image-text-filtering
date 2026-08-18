<!-- last_verified: 2026-08-18 -->
# Feature: Filter Runs

## Purpose
The primary entity: a configurable DataComp-style filter job that streams raw
WebDataset shards from B2, scores image-text alignment with CLIP, and writes
high-quality filtered shards plus quality metrics back to B2.

## Used By
- UI: `/runs` (list + create/edit/delete/run), `/runs/[id]` (detail + per-shard metrics + per-pair CLIP scores + a determinate progress bar while running)
- API: `GET/POST /runs`, `GET/PUT/DELETE /runs/{run_id}`, `POST /runs/{run_id}/run`, `GET /runs/{run_id}/pairs`, `GET /runs/stats`, `GET /runs/source-prefixes`
- Job: FastAPI `BackgroundTasks` runs the CLIP filter engine off the request path

## Core Functions
- `services/api/app/service/filtering.py` — the CLIP filter engine (lazy-imports torch/open_clip/webdataset; ML stack confined here)
- `services/api/app/service/filter_ops.py` — pure keep/drop logic + percentile threshold (no ML)
- `services/api/app/service/runs.py` — create/read/edit/delete + `execute_run` orchestration
- `services/api/app/repo/runs_store.py` — run manifest + artifact persistence on B2 (boto3)
- `services/api/app/runtime/runs.py` — route handlers + BackgroundTasks scheduling
- `services/api/app/service/runs.py::get_run_pairs` — reads `metrics/<id>/*.json` into the per-pair (kept AND dropped) response for `GET /runs/{id}/pairs`
- `apps/web/src/components/runs/*` — run table, create/edit form, detail view, dialogs; `run-pair-scores.tsx` renders the per-pair kept-vs-dropped table

## Canonical Files
- Filter engine: `services/api/app/service/filtering.py`
- Create/edit form (selector + safe-default-hint pattern): `apps/web/src/components/runs/run-form.tsx`

## Inputs
- `RunConfig` (source): name (free text), source_prefix (Select), clip_model (Select: ViT-B-32/ViT-L-14), strategy (RadioGroup: clip_score/basic/image_based/text_based), clip_percentile, min_resolution, caption_min/max_tokens, dedup (Switch)

## Outputs
- `runs/<id>/manifest.json` — the run entity (config, status, stats, per-shard metrics, and `progress` = `{shards_done, shards_total}` while running)
- `filtered/<id>/*.tar` — re-packed WebDataset shards of the passing pairs (kept only)
- `metrics/<id>/*.json` — per-shard metrics (per-pair CLIP score + kept flag for EVERY pair, kept and dropped)
- `GET /runs/{id}/pairs` → `RunPairMetrics` — every scored pair (kept AND dropped) with its CLIP score + the keep threshold, sorted by score; the only place a dropped pair's low score is visible (the filtered `.tar` holds kept pairs only)
- Side effects: reads `pool/` shards; invalidates the bucket listing cache on writes

## Flow
- **create** → mint a `pending` manifest (`POST /runs`)
- **edit** → replace a *pending* run's config (`PUT /runs/{id}`); completed/running runs are immutable (detail view offers "Clone")
- **run** → mark `running` and seed `progress` with the shard count (`POST /runs/{id}/run`); the engine auto-detects device (CUDA → MPS → CPU), scores every pair, persists `progress.shards_done` after each shard (so the 2s poll advances a determinate bar), applies the strategy, writes filtered shards + metrics, sets `completed`
- **read** → `GET /runs/{id}`; the UI polls every 2s while `running` and drives the progress bar from `progress`. A completed run's detail also fetches `GET /runs/{id}/pairs` for the per-pair kept-vs-dropped table
- **delete** → remove the manifest + scoped `filtered/<id>/` and `metrics/<id>/` (never other runs or the raw pool)

## Edge Cases
- ML stack absent (base venv) → `FilterEngineUnavailableError`, run persisted `failed` with an actionable message; the POST never 500s
- Empty pool → run persisted `failed` pointing at the seed script
- Edit a non-pending run → `409`
- Missing run id → `404`

## UX States
- Empty: "No filter runs yet" with a create CTA
- Loading: skeleton rows / spinner
- Running: auto-refreshing detail with a determinate progress bar ("N of M shards") driven by `progress`
- Completed: results + per-shard metrics + a per-pair CLIP-score table (kept vs dropped, with the keep threshold)
- Error/Failed: destructive alert showing the engine's message

## Verification
- Test files: `services/api/tests/test_runs.py`, `services/api/tests/test_structure.py`
- Required cases: create/get/list/update/delete, edit-conflict on a non-pending run, start returns `running` and seeds `progress` total, `execute_run` persists mid-run progress via the injected callback, `GET /runs/{id}/pairs` surfaces dropped pairs' low scores (404 on a missing run), engine-error persists `failed`, ML-stack-only-in-filtering boundary
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: run tests green; a real run (with `requirements-ml.txt` installed) writes filtered shards + metrics to B2 and reports a non-zero storage reduction

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Pool Explorer](pool-explorer.md)
- [App Workflows](../app-workflows.md)
