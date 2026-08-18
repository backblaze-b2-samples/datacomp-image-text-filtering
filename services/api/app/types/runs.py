"""Pydantic models for Filter Runs — the primary entity.

A Filter Run is persisted as a single B2 manifest (`runs/<id>/manifest.json`),
so these models are also the on-disk schema. No database.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FilterStrategy(StrEnum):
    """DataComp baseline filter families (mirrors DataComp `baselines.py`)."""

    clip_score = "clip_score"
    basic = "basic"
    image_based = "image_based"
    text_based = "text_based"


class ClipModel(StrEnum):
    """open_clip scoring models (ungated OpenAI CLIP weights)."""

    vit_b_32 = "ViT-B-32"
    vit_l_14 = "ViT-L-14"


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class RunConfig(BaseModel):
    """The knobs a Filter Run is executed with. All finite-value fields are
    enums/bounded numbers so the create/edit form uses selectors, not free text
    (only `name` is free text)."""

    name: str = Field(min_length=1, max_length=100)
    source_prefix: str = Field(default="pool/", min_length=1, max_length=256)
    clip_model: ClipModel = ClipModel.vit_b_32
    strategy: FilterStrategy = FilterStrategy.clip_score
    # Fraction of pairs to KEEP (top-scoring). 0.30 = DataComp clip_score default.
    clip_percentile: float = Field(default=0.30, ge=0.0, le=1.0)
    min_resolution: int = Field(default=64, ge=1, le=8192)
    caption_min_tokens: int = Field(default=2, ge=0, le=1000)
    caption_max_tokens: int = Field(default=256, ge=1, le=100000)
    dedup: bool = True


class ShardMetric(BaseModel):
    shard: str
    pairs_in: int
    pairs_kept: int
    pairs_dropped: int
    mean_clip_score: float
    kept_mean_clip_score: float
    output_key: str | None = None
    metrics_key: str | None = None


class FilterStats(BaseModel):
    total_pairs_in: int
    total_pairs_kept: int
    total_pairs_dropped: int
    reduction_pct: float
    mean_clip_score: float
    clip_score_threshold: float | None = None
    device: str | None = None


class RunProgress(BaseModel):
    """Mid-run advancement for a determinate progress bar. `shards_total` is set
    at start (from the pool listing) so the bar has a denominator on the first
    poll; `shards_done` is bumped after each shard is scored in pass 1."""

    shards_done: int
    shards_total: int


class FilterRun(BaseModel):
    id: str
    config: RunConfig
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    source_shard_count: int = 0
    output_prefix: str | None = None
    metrics_prefix: str | None = None
    shard_metrics: list[ShardMetric] = Field(default_factory=list)
    stats: FilterStats | None = None
    progress: RunProgress | None = None
    error: str | None = None


class RunPairMetric(BaseModel):
    """One scored image-text pair from a completed run's metrics JSON — the
    per-pair kept-vs-dropped detail the aggregate `ShardMetric` rows omit."""

    key: str
    shard: str
    caption: str
    clip_score: float
    kept: bool


class RunPairMetrics(BaseModel):
    """Every scored pair of a completed run (kept AND dropped), sorted by score,
    so the UI can show which pairs CLIP dropped and why."""

    run_id: str
    clip_score_threshold: float | None = None
    pair_count: int
    pairs: list[RunPairMetric]


class RunCreateRequest(RunConfig):
    """Body for POST /runs (same validated fields as RunConfig)."""


class RunUpdateRequest(RunConfig):
    """Body for PUT /runs/{id} — replaces a *pending* run's config."""


class DeleteRunResponse(BaseModel):
    deleted: bool
    id: str


class SourcePrefix(BaseModel):
    prefix: str
    shard_count: int


class RunStats(BaseModel):
    total_runs: int
    completed_runs: int
    running_runs: int
    failed_runs: int
    total_pairs_kept: int
    total_pairs_dropped: int
    avg_reduction_pct: float
