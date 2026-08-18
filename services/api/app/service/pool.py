"""Pool Explorer — the sample-specific, prefix-SCOPED asset explorer.

Browses the `pool/` (raw) and `filtered/` (output) prefixes at shard granularity
and opens a shard to reveal the image-text pairs inside it (thumbnail + caption +
CLIP score + kept/dropped). Scoped to the sample's own prefixes — contrast with
the KEPT full-bucket Bucket Explorer (`service/files.py`).
"""

import base64
import io
import logging

from PIL import Image

from app.repo import get_object_bytes, list_shards, load_json
from app.service.filter_ops import read_webdataset_pairs
from app.types.formatting import humanize_bytes
from app.types.pool import ImageTextPair, ShardContents, ShardSummary

logger = logging.getLogger(__name__)

POOL_PREFIX = "pool/"
FILTERED_PREFIX = "filtered/"
METRICS_PREFIX = "metrics/"
# Cap pairs returned per shard so a data-URL response stays small.
MAX_PAIRS = 60
THUMB_MAX = 96


class ShardScopeError(Exception):
    """Raised when a key is outside the pool/ and filtered/ prefixes."""

    def __init__(self, detail: str = "Shard is outside the pool/ or filtered/ scope"):
        self.detail = detail
        super().__init__(detail)


def scope_of(key: str) -> str:
    if key.startswith(POOL_PREFIX):
        return "pool"
    if key.startswith(FILTERED_PREFIX):
        return "filtered"
    raise ShardScopeError()


def list_scope_shards(scope: str) -> list[ShardSummary]:
    if scope not in ("pool", "filtered"):
        raise ShardScopeError(f"Unknown scope {scope!r} (expected pool or filtered)")
    prefix = POOL_PREFIX if scope == "pool" else FILTERED_PREFIX
    summaries: list[ShardSummary] = []
    for shard in list_shards(prefix):
        key = shard["key"]
        run_id = None
        if scope == "filtered":
            rest = key[len(FILTERED_PREFIX) :]
            run_id = rest.split("/", 1)[0] if "/" in rest else None
        summaries.append(
            ShardSummary(
                key=key,
                name=key.rsplit("/", 1)[-1],
                size_bytes=shard["size"],
                size_human=humanize_bytes(shard["size"]),
                scope=scope,
                run_id=run_id,
            )
        )
    return summaries


def _thumbnail(img_bytes: bytes) -> str | None:
    try:
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        return None
    image.thumbnail((THUMB_MAX, THUMB_MAX))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _dimensions(img_bytes: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(io.BytesIO(img_bytes)) as image:
            return image.size
    except Exception:
        return (None, None)


def _metrics_index(filtered_key: str) -> dict[str, dict]:
    """For a `filtered/<run>/<shard>.tar` key, load the matching per-shard
    metrics JSON and index its pair records by key (scores + kept flags)."""
    rest = filtered_key[len(FILTERED_PREFIX) :]
    parts = rest.split("/", 1)
    if len(parts) != 2:
        return {}
    run_id, shard = parts
    stem = shard[:-4] if shard.endswith(".tar") else shard
    doc = load_json(f"{METRICS_PREFIX}{run_id}/{stem}.json")
    if not doc:
        return {}
    return {p["key"]: p for p in doc.get("pairs", [])}


def get_shard_contents(key: str) -> ShardContents:
    """Open a shard and return the image-text pairs inside it. Raises
    ShardScopeError for out-of-scope keys, RuntimeError on a storage failure."""
    scope = scope_of(key)
    data = get_object_bytes(key)
    raw = read_webdataset_pairs(data)
    scores = _metrics_index(key) if scope == "filtered" else {}
    pairs: list[ImageTextPair] = []
    for base, img_bytes, caption in raw[:MAX_PAIRS]:
        info = scores.get(base)
        width, height = _dimensions(img_bytes)
        pairs.append(
            ImageTextPair(
                key=base,
                caption=caption,
                thumbnail_data_url=_thumbnail(img_bytes),
                width=info["width"] if info else width,
                height=info["height"] if info else height,
                clip_score=info["clip_score"] if info else None,
                kept=info["kept"] if info else None,
            )
        )
    return ShardContents(
        key=key, scope=scope, pair_count=len(raw), shown=len(pairs), pairs=pairs
    )
