"""Pydantic models for the Pool Explorer — the scoped asset explorer that opens
a WebDataset `.tar` shard and shows the image-text pairs inside it."""

from __future__ import annotations

from pydantic import BaseModel


class ShardSummary(BaseModel):
    key: str
    name: str
    size_bytes: int
    size_human: str
    scope: str  # "pool" (raw) or "filtered" (output)
    run_id: str | None = None


class ImageTextPair(BaseModel):
    key: str
    caption: str
    thumbnail_data_url: str | None = None
    width: int | None = None
    height: int | None = None
    # Populated only for filtered shards (read from the run's metrics JSON).
    clip_score: float | None = None
    kept: bool | None = None


class ShardContents(BaseModel):
    key: str
    scope: str
    pair_count: int
    shown: int
    pairs: list[ImageTextPair]
