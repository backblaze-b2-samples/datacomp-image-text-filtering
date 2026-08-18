<!-- last_verified: 2026-08-18 -->
# App Workflows

User journeys inside the application.

## Create and Run a Filter Run (primary)

- User navigates to `/runs` and clicks **New run**
- The create form uses selectors for every finite field (source pool, CLIP model, strategy, dedup) and free text only for the run name; safe defaults are surfaced as guidance (placeholder / description), never auto-filled by a button
- On submit, a `pending` run is created (a B2 manifest) and the user lands on `/runs/[id]`
- The user reviews the config; a **pending** run can be **edited** (config pre-filled) or **deleted**
- Clicking **Start run** marks it `running` and schedules a background task: the CLIP filter engine streams `pool/` shards from B2, auto-detects the device (CUDA → MPS → CPU), scores every image-text pair, applies the strategy, and writes `filtered/<id>/*.tar` + `metrics/<id>/*.json` back to B2
- The detail view auto-refreshes every 2s while running, then shows kept/dropped counts, storage-reduction %, mean CLIP score, threshold, device, and a per-shard metrics table
- A completed/running run is immutable — the detail view offers **Clone** to start a new pending run from the same config
- If the ML stack is not installed (or the pool is empty), the run is persisted `failed` with an actionable message — the Start POST never errors
- See: [Filter Runs](features/filter-runs.md)

## Explore the Pool

- User navigates to `/pool` and picks a scope tab: **Pool (raw)** or **Filtered (output)**
- The shard list loads for that scope; clicking a shard opens it
- The pairs grid shows each image-text pair: thumbnail, caption, dimensions, and — for filtered shards — its CLIP score and a kept/dropped badge (read from the run's metrics JSON)
- The explorer is scoped to `pool/` and `filtered/` (contrast with the full-bucket Bucket Explorer); out-of-scope keys are rejected server-side
- See: [Pool Explorer](features/pool-explorer.md)

## Ingest shards (upload)

- User navigates to `/upload` (Ingest)
- Drops or selects files; the client validates size (max 100MB) and type
- Files upload **directly from the browser to B2** (a presigned PUT) with a determinate progress bar, then an indeterminate "Verifying upload…" phase while the API HEADs and magic-byte-sniffs the stored object
- The seed script (`services/api/scripts/seed_pool.py`) is the keyless alternative that populates a synthetic demo pool
- See: [Ingest (File Upload)](features/file-upload.md)

## Browse the Bucket (Bucket Explorer)

- User navigates to `/files` (Bucket Explorer)
- The page loads the most recent objects across the WHOLE bucket — pool shards, filtered output, run manifests, metrics — in a tree view with preview / download / delete
- Arriving at `/files?preview=<key>` opens a specific object's preview directly (used by the ⌘K palette)
- See: [Bucket Explorer](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Stat cards show total runs, completed runs, pairs kept, and average storage reduction
- The recent runs table links each run to its detail view; a **New run** button opens the create dialog
- Empty state: "No runs yet" with a create CTA
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner states the page is mostly a demonstration: only **Theme** is wired up for real (via `next-themes`); the rest persists to `localStorage` only
- See: [Settings](features/settings.md)
