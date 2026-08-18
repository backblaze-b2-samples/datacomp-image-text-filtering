<!-- last_verified: 2026-08-18 -->
# Feature: Pool Explorer

## Purpose
Inspect the image-text pairs inside a WebDataset shard, scoped to the sample's
own `pool/` (raw) and `filtered/` (output) prefixes. What each tab can show
differs, and the empty-state guidance is written per-tab so it never
over-promises:
- **Pool (raw)** — pre-filter pairs: thumbnail, caption, resolution. There is no
  CLIP score or kept/dropped decision here (those only exist after a run).
- **Filtered (output)** — KEPT pairs only, each with a "kept" badge + CLIP score.

The full kept-vs-dropped-with-scores breakdown — including the DROPPED pairs and
their low scores, which no shard `.tar` contains — lives on the run detail page
(`GET /runs/{id}/pairs`, rendered by `run-pair-scores.tsx`), not here.

## Used By
- UI: `/pool` page (scope tabs → shard list → pairs grid)
- API: `GET /pool/shards?scope=pool|filtered`, `GET /pool/shard?key=...`

## Core Functions
- `services/api/app/service/pool.py` — list scoped shards, open a shard, build thumbnails, cross-reference metrics
- `services/api/app/service/filter_ops.py::read_webdataset_pairs` — stdlib tarfile shard reader (shared with the engine)
- `services/api/app/runtime/pool.py` — route handlers (scope enforcement)
- `apps/web/src/components/pool/pool-explorer.tsx` — master-detail explorer UI

## Canonical Files
- Scoped explorer service: `services/api/app/service/pool.py`

## Inputs
- `scope`: "pool" | "filtered" (query)
- `key`: a shard object key, validated to be under `pool/` or `filtered/`

## Outputs
- `GET /pool/shards` → `ShardSummary[]`
- `GET /pool/shard` → `ShardContents` (pairs with base64 thumbnail data URLs, dimensions, and — for filtered shards — CLIP score + kept flag read from the run's `metrics/<id>/*.json`)

## Flow
- Pick a scope (Pool or Filtered) → shard list loads
- Click a shard → the API reads it from B2, extracts up to 60 pairs, returns thumbnails + captions (+ scores/kept for filtered)
- The grid renders each pair with a kept/dropped badge and its CLIP score

## Edge Cases
- Key outside `pool/`/`filtered/` → `400` (scope enforced server-side)
- Unreadable/missing shard → `502`
- Pool (raw) shards have no metrics → score/kept shown as "—"
- Large shard → capped at 60 pairs; `pair_count` vs `shown` are reported

## UX States
- Empty (no shard selected): per-tab "Open a shard" guidance — the Pool tab
  promises only thumbnail/caption/resolution and points to the run detail for
  scores + kept/dropped; the Filtered tab promises kept pairs + CLIP score
- Empty (no shards): "No raw shards" / "No filtered shards" (points at the seed script / running a filter)
- Loading: skeleton grid
- Loaded: image-text pair grid
- Error: inline retry

## Verification
- Test files: `services/api/tests/test_pool.py`
- Required cases: list pool/filtered shards, run_id extraction for filtered, bad scope 400, open shard returns pairs with data-URL thumbnails, out-of-scope key 400
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_pool.py`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: pool tests green; the contrast with the full-bucket Bucket Explorer is preserved (this explorer is prefix-scoped)

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Filter Runs](filter-runs.md)
- [Bucket Explorer](file-browser.md)
