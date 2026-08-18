<!-- last_verified: 2026-08-18 -->
# Initial scaffold — DataComp Image-Text Filtering

Status: complete.

Scaffolded from the vibe-coding-starter-kit template into a DataComp-style
image-text dataset curation app on Backblaze B2.

## What was built
- **Filter Runs** (primary entity) — create/read/edit/delete/run, persisted as B2
  manifests (`runs/<id>/manifest.json`), full lifecycle in the UI.
- **Real CLIP filter engine** — `service/filtering.py` runs open_clip CLIP scoring,
  writes filtered `.tar` shards (`filtered/<id>/`) and per-shard metrics
  (`metrics/<id>/`) back to B2. Device auto-detected (CUDA → MPS → CPU).
- **Pool Explorer** — scoped shard viewer for `pool/` + `filtered/`.
- **Bucket Explorer** (kept full-bucket browse) and **Ingest** (presigned upload).
- **Seed script** — synthetic, keyless, distinguishable image-text pool.

## Invariants added
- ML stack (`torch`/`torchvision`/`open_clip`/`webdataset`) lazy-imported and
  confined to `service/filtering.py`, shipped in `requirements-ml.txt` (excluded
  from `pnpm run setup` and CI). Enforced by
  `tests/test_structure.py::test_ml_stack_only_in_filtering`.
- Standardized `B2_*` env names; S3 endpoint built at runtime from `B2_REGION`
  (no hardcoded region). Custom user agent `b2ai-datacomp-image-text-filtering`.

## Related Docs
- [Filter Runs](../../features/filter-runs.md)
- [Pool Explorer](../../features/pool-explorer.md)
- [ARCHITECTURE.md](../../../ARCHITECTURE.md)
