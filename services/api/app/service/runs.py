"""Filter Run orchestration: create / read / edit / delete / run.

Persists every run as a B2 manifest via `repo.runs_store` (no database) and
kicks off the real CLIP filter engine (`service.filtering`). `execute_run` is
the background-task entrypoint and NEVER raises — a failed run is persisted with
status `failed`, so the POST that starts it never 500s.
"""

import logging
import uuid
from datetime import UTC, datetime

from app.repo import (
    delete_run as _repo_delete_run,
)
from app.repo import (
    get_object_bytes,
    list_manifests,
    list_shards,
    load_manifest,
    put_bytes,
    save_manifest,
)
from app.service import filtering
from app.types.runs import (
    FilterRun,
    RunConfig,
    RunCreateRequest,
    RunStats,
    RunStatus,
    RunUpdateRequest,
    SourcePrefix,
)

logger = logging.getLogger(__name__)

POOL_PREFIX = "pool/"


class RunNotFoundError(Exception):
    def __init__(self, detail: str = "Filter run not found"):
        self.detail = detail
        super().__init__(detail)


class RunNotEditableError(Exception):
    def __init__(self, detail: str = "Only pending runs can be edited"):
        self.detail = detail
        super().__init__(detail)


def _persist(run: FilterRun) -> FilterRun:
    run.updated_at = datetime.now(UTC)
    save_manifest(run.id, run.model_dump(mode="json"))
    return run


def create_run(req: RunCreateRequest) -> FilterRun:
    now = datetime.now(UTC)
    run_id = uuid.uuid4().hex[:12]
    run = FilterRun(
        id=run_id,
        config=RunConfig(**req.model_dump()),
        status=RunStatus.pending,
        created_at=now,
        updated_at=now,
        output_prefix=f"filtered/{run_id}/",
        metrics_prefix=f"metrics/{run_id}/",
    )
    return _persist(run)


def get_run(run_id: str) -> FilterRun:
    manifest = load_manifest(run_id)
    if manifest is None:
        raise RunNotFoundError()
    return FilterRun.model_validate(manifest)


def list_runs() -> list[FilterRun]:
    runs = [FilterRun.model_validate(m) for m in list_manifests()]
    runs.sort(key=lambda r: r.created_at, reverse=True)
    return runs


def update_run(run_id: str, req: RunUpdateRequest) -> FilterRun:
    run = get_run(run_id)
    if run.status != RunStatus.pending:
        raise RunNotEditableError(
            "Completed and running runs are immutable — clone to a new run instead."
        )
    run.config = RunConfig(**req.model_dump())
    return _persist(run)


def delete_run(run_id: str) -> None:
    get_run(run_id)  # raise 404 if it doesn't exist
    _repo_delete_run(run_id)


def start_run(run_id: str) -> FilterRun:
    """Mark a run as running and persist it. The heavy work happens in
    `execute_run` (a background task). A run already running is left as-is."""
    run = get_run(run_id)
    if run.status == RunStatus.running:
        return run
    run.status = RunStatus.running
    run.error = None
    return _persist(run)


def execute_run(run_id: str) -> None:
    """Background-task entrypoint. NEVER raises — persists `failed` on any error."""
    try:
        run = get_run(run_id)
    except RunNotFoundError:
        logger.warning("execute_run: run %s vanished before execution", run_id)
        return
    try:
        result = filtering.run_filter(run, get_object_bytes, put_bytes, list_shards)
        _persist(result)
    except filtering.FilterEngineUnavailableError as e:
        logger.warning("Filter run %s unavailable: %s", run_id, e)
        run.status = RunStatus.failed
        run.error = str(e)
        _persist(run)
    except Exception as e:
        logger.exception("Filter run %s failed", run_id)
        run.status = RunStatus.failed
        run.error = f"Filter run failed: {e}"
        _persist(run)


def discover_source_prefixes() -> list[SourcePrefix]:
    """Distinct directory prefixes under `pool/` that contain `.tar` shards,
    for the create-form source selector."""
    counts: dict[str, int] = {}
    for shard in list_shards(POOL_PREFIX):
        parent = shard["key"].rsplit("/", 1)[0] + "/"
        counts[parent] = counts.get(parent, 0) + 1
    prefixes = [SourcePrefix(prefix=p, shard_count=c) for p, c in counts.items()]
    prefixes.sort(key=lambda p: p.prefix)
    if not prefixes:
        # Always offer the canonical pool prefix so the form has a default even
        # before the pool is seeded.
        prefixes.append(SourcePrefix(prefix=POOL_PREFIX, shard_count=0))
    return prefixes


def run_stats() -> RunStats:
    runs = list_runs()
    completed = [r for r in runs if r.status == RunStatus.completed]
    running = sum(1 for r in runs if r.status == RunStatus.running)
    failed = sum(1 for r in runs if r.status == RunStatus.failed)
    kept = sum(r.stats.total_pairs_kept for r in completed if r.stats)
    dropped = sum(r.stats.total_pairs_dropped for r in completed if r.stats)
    reductions = [r.stats.reduction_pct for r in completed if r.stats]
    return RunStats(
        total_runs=len(runs),
        completed_runs=len(completed),
        running_runs=running,
        failed_runs=failed,
        total_pairs_kept=kept,
        total_pairs_dropped=dropped,
        avg_reduction_pct=round(sum(reductions) / len(reductions), 2)
        if reductions
        else 0.0,
    )
