import logging

# Sync `def` handlers on purpose: the whole chain is blocking boto3, so
# Starlette runs these in its threadpool (see runtime/files.py rationale).
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.service.runs import (
    RunNotEditableError,
    RunNotFoundError,
    create_run,
    delete_run,
    discover_source_prefixes,
    execute_run,
    get_run,
    get_run_pairs,
    list_runs,
    run_stats,
    start_run,
    update_run,
)
from app.types import (
    DeleteRunResponse,
    FilterRun,
    RunCreateRequest,
    RunPairMetrics,
    RunStats,
    RunUpdateRequest,
    SourcePrefix,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like the file routes, these are intentionally UNAUTHENTICATED and
# bucket-wide (single-tenant demo stance — see docs/SECURITY.md).


# Static paths declared BEFORE /runs/{run_id} so `stats` / `source-prefixes`
# are never captured as a run id.
@router.get("/runs/stats", response_model=RunStats)
def run_stats_endpoint():
    return run_stats()


@router.get("/runs/source-prefixes", response_model=list[SourcePrefix])
def source_prefixes_endpoint():
    return discover_source_prefixes()


@router.get("/runs", response_model=list[FilterRun])
def list_runs_endpoint():
    return list_runs()


@router.post("/runs", response_model=FilterRun)
def create_run_endpoint(req: RunCreateRequest):
    return create_run(req)


@router.get("/runs/{run_id}", response_model=FilterRun)
def get_run_endpoint(run_id: str):
    try:
        return get_run(run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/runs/{run_id}/pairs", response_model=RunPairMetrics)
def get_run_pairs_endpoint(run_id: str):
    """Per-pair CLIP scores (kept AND dropped) for a run, read from its metrics
    JSON — the only place a dropped pair's low score is visible in the UI."""
    try:
        return get_run_pairs(run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.put("/runs/{run_id}", response_model=FilterRun)
def update_run_endpoint(run_id: str, req: RunUpdateRequest):
    try:
        return update_run(run_id, req)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RunNotEditableError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None


@router.delete("/runs/{run_id}", response_model=DeleteRunResponse)
def delete_run_endpoint(run_id: str):
    try:
        delete_run(run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    logger.info("Filter run deleted: id=%s", run_id)
    return DeleteRunResponse(deleted=True, id=run_id)


@router.post("/runs/{run_id}/run", response_model=FilterRun)
def start_run_endpoint(run_id: str, background_tasks: BackgroundTasks):
    """Kick off a filter run. Marks it `running`, schedules the real CLIP filter
    as a background task, and returns immediately. Execution NEVER 500s the POST:
    a missing ML stack or empty pool persists the run as `failed`."""
    try:
        run = start_run(run_id)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    background_tasks.add_task(execute_run, run_id)
    return run
