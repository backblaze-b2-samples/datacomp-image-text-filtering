import logging

# Sync `def` handlers: blocking boto3 work runs in Starlette's threadpool.
from fastapi import APIRouter, HTTPException

from app.service.pool import (
    ShardScopeError,
    get_shard_contents,
    list_scope_shards,
)
from app.types import ShardContents, ShardSummary

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: unauthenticated, single-tenant demo — see docs/SECURITY.md. The
# scope is enforced to pool/ and filtered/ so this explorer stays prefix-scoped.


@router.get("/pool/shards", response_model=list[ShardSummary])
def list_pool_shards_endpoint(scope: str = "pool"):
    try:
        return list_scope_shards(scope)
    except ShardScopeError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None


@router.get("/pool/shard", response_model=ShardContents)
def get_pool_shard_endpoint(key: str):
    if not key:
        raise HTTPException(status_code=400, detail="key is required")
    try:
        return get_shard_contents(key)
    except ShardScopeError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Failed to read shard from storage"
        ) from None
