<!-- last_verified: 2026-08-18 -->
# Feature: Dashboard

## Purpose
Provide an at-a-glance overview of filtering activity: how many runs, how many
completed, how many image-text pairs kept, and the average storage reduction.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /runs/stats`, `GET /runs`

## Core Functions
- `apps/web/src/components/dashboard/run-stats-cards.tsx` — 4 stat cards (total runs, completed, pairs kept, avg reduction)
- `apps/web/src/components/dashboard/recent-runs-table.tsx` — most recent runs with status + reduction
- `apps/web/src/lib/queries.ts` — `useRunStats()`, `useRuns()`
- `services/api/app/runtime/runs.py` — `GET /runs/stats` handler
- `services/api/app/service/runs.py` — `run_stats()` aggregation over run manifests

## Canonical Files
- Dashboard cards: `apps/web/src/components/dashboard/run-stats-cards.tsx`
- Stats aggregation: `services/api/app/service/runs.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /runs/stats` → `RunStats` (total_runs, completed_runs, running_runs, failed_runs, total_pairs_kept, total_pairs_dropped, avg_reduction_pct)
- `GET /runs` → `FilterRun[]` (recent runs table, newest-first)

## Flow
- Page loads → parallel calls for run stats and the run list
- Stat cards show totals; the recent runs table links each run to its detail view
- A "New run" button opens the create dialog

## Edge Cases
- API unavailable → error state with retry
- No runs yet → empty state with a create CTA
- Runs still `pending`/`running` → excluded from kept/reduction aggregates (only completed runs contribute)

## UX States
- Loading: skeleton cards + rows
- Empty: "No runs yet" with a create CTA
- Loaded: populated cards + recent runs table

## Verification
- Test files: `services/api/tests/test_runs.py` (`test_run_stats_empty`, lifecycle tests)
- Required cases: empty stats, stats after completed runs, API error fallback
- Focused verify command: `services/api/.venv/bin/python -m pytest tests/test_runs.py`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Filter Runs](filter-runs.md)
- [App Workflows](../app-workflows.md)
