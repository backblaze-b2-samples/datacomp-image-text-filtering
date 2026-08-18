"""DataComp-style CLIP-score filtering engine — the marquee feature.

The heavy ML stack (torch / torchvision / open_clip / webdataset) is
LAZY-imported inside the functions here and appears ONLY in this module — a
structural test enforces that. It ships in `requirements-ml.txt`, excluded from
`pnpm run setup` and CI, so the app boots and static gates pass without it.

If the stack is absent, `run_filter` raises `FilterEngineUnavailableError`; the
caller persists the run as `failed` so the POST never 500s. Everything here is
REAL — real open_clip CLIP scoring, real filtered `.tar` shards and metrics JSON
written back to B2. Nothing is mocked to run cheaply.
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.service.filter_ops import (
    ScoredPair,
    apply_filters,
    count_tokens,
    read_webdataset_pairs,
)
from app.types.runs import FilterRun, FilterStats, RunProgress, RunStatus, ShardMetric

logger = logging.getLogger(__name__)

ML_HINT = (
    "The CLIP filter engine needs the ML stack. Install it into the API venv: "
    "`services/api/.venv/bin/pip install -r services/api/requirements-ml.txt` "
    "(torch, torchvision, open_clip_torch, webdataset). It is intentionally "
    "excluded from `pnpm run setup` and CI."
)

GetBytes = Callable[[str], bytes]
PutBytes = Callable[[str, bytes, str], None]
ListShards = Callable[[str], list[dict]]
# (shards_done, shards_total) — invoked after each shard is scored in pass 1 so
# the caller can persist mid-run progress. Persistence is injected here on
# purpose: this module stays ML-only and never imports repo/boto3.
ProgressCallback = Callable[[int, int], None]


class FilterEngineUnavailableError(RuntimeError):
    """Raised when the run cannot execute (ML stack missing, or no input pool).

    The caller catches this and persists the run as `failed`, so a POST that
    kicks off a run never returns a 500 just because the heavy stack is absent.
    """


def detect_device() -> str:
    """Runtime device auto-detect: CUDA -> Apple MPS -> CPU (default CPU).

    Never hard-requires a GPU. open_clip runs on MPS with occasional CPU op
    fallbacks (acceptable); a machine with neither uses CPU.
    """
    import torch

    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _load_model(model_name: str, device: str):
    import open_clip

    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name, pretrained="openai"
    )
    tokenizer = open_clip.get_tokenizer(model_name)
    model = model.to(device).eval()
    return model, preprocess, tokenizer


def _ahash(image) -> str:
    """8x8 average hash as a 64-bit hex string — cheap near-duplicate key."""
    small = image.convert("L").resize((8, 8))
    pixels = list(small.getdata())
    avg = (sum(pixels) / len(pixels)) if pixels else 0
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | (1 if pixel >= avg else 0)
    return f"{bits:016x}"


def _score_shard(shard_bytes, model, preprocess, tokenizer, device):
    """Score every image-text pair in one shard with CLIP.

    Returns (scored_pairs, payloads) where payloads[key] = (image_bytes, caption)
    for re-packing the kept pairs into the output shard.
    """
    import torch
    from PIL import Image

    scored: list[ScoredPair] = []
    payloads: dict[str, tuple[bytes, str]] = {}
    for key, img_bytes, caption in read_webdataset_pairs(shard_bytes):
        try:
            image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception:
            logger.warning("Skipping undecodable image: %s", key)
            continue
        width, height = image.size
        with torch.no_grad():
            image_input = preprocess(image).unsqueeze(0).to(device)
            text_input = tokenizer([caption]).to(device)
            img_feat = model.encode_image(image_input)
            txt_feat = model.encode_text(text_input)
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
            txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
            score = float((img_feat @ txt_feat.T).squeeze().item())
        scored.append(
            ScoredPair(
                key=key,
                caption=caption,
                score=score,
                width=width,
                height=height,
                n_tokens=count_tokens(caption),
                img_hash=_ahash(image),
            )
        )
        payloads[key] = (img_bytes, caption)
    return scored, payloads


def _write_filtered_shard(output_key, kept, payloads, put_bytes) -> None:
    import webdataset

    buffer = io.BytesIO()
    with webdataset.TarWriter(buffer, encoder=False) as sink:
        for pair in kept:
            img_bytes, caption = payloads[pair.key]
            sink.write(
                {
                    "__key__": pair.key,
                    "jpg": img_bytes,
                    "txt": caption.encode("utf-8"),
                }
            )
    put_bytes(output_key, buffer.getvalue(), "application/x-tar")


def _write_metrics(metrics_key, shard_name, scored, keep_by_key, threshold, device, put_bytes) -> None:
    pairs = [
        {
            "key": p.key,
            "caption": p.caption,
            "clip_score": round(p.score, 4),
            "kept": bool(keep_by_key.get(p.key)),
            "width": p.width,
            "height": p.height,
            "n_tokens": p.n_tokens,
        }
        for p in scored
    ]
    doc = {
        "shard": shard_name,
        "clip_score_threshold": round(threshold, 4),
        "device": device,
        "pair_count": len(scored),
        "pairs": pairs,
    }
    put_bytes(metrics_key, json.dumps(doc, indent=2).encode("utf-8"), "application/json")


def run_filter(
    run: FilterRun,
    get_bytes: GetBytes,
    put_bytes: PutBytes,
    list_shards: ListShards,
    on_progress: ProgressCallback | None = None,
) -> FilterRun:
    """Stream pool shards from B2, CLIP-score them, and write filtered shards +
    metrics back to B2. Returns the run updated to `completed` with full stats.

    Raises FilterEngineUnavailableError when the ML stack is missing or the pool
    is empty; the caller persists `failed` in both cases.
    """
    try:
        import open_clip  # noqa: F401
        import torch  # noqa: F401
        import webdataset  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as e:
        raise FilterEngineUnavailableError(f"{ML_HINT} (import error: {e})") from e

    device = detect_device()
    logger.info(
        "Filter run %s starting: device=%s model=%s strategy=%s",
        run.id,
        device,
        run.config.clip_model.value,
        run.config.strategy.value,
    )
    model, preprocess, tokenizer = _load_model(run.config.clip_model.value, device)

    shards = list_shards(run.config.source_prefix)
    if not shards:
        raise FilterEngineUnavailableError(
            f"No .tar shards found under '{run.config.source_prefix}'. Seed a pool "
            "first: `python services/api/scripts/seed_pool.py`."
        )

    # Pass 1: score every pair (global percentile, like DataComp's clip_score).
    per_shard: list[tuple[str, list[ScoredPair], dict]] = []
    all_pairs: list[ScoredPair] = []
    for shard in shards:
        name = shard["key"].rsplit("/", 1)[-1]
        scored, payloads = _score_shard(
            get_bytes(shard["key"]), model, preprocess, tokenizer, device
        )
        per_shard.append((name, scored, payloads))
        all_pairs.extend(scored)
        if on_progress is not None:
            # len(per_shard) shards are now scored out of len(shards) total.
            on_progress(len(per_shard), len(shards))

    flags, threshold = apply_filters(all_pairs, run.config)
    keep_by_key = {p.key: f for p, f in zip(all_pairs, flags, strict=True)}

    # Pass 2: re-pack kept pairs and write per-shard metrics.
    shard_metrics: list[ShardMetric] = []
    total_in = total_kept = 0
    score_sum = 0.0
    for name, scored, payloads in per_shard:
        stem = name[:-4] if name.endswith(".tar") else name
        kept = [p for p in scored if keep_by_key.get(p.key)]
        output_key = f"{run.output_prefix}{name}"
        metrics_key = f"{run.metrics_prefix}{stem}.json"
        _write_filtered_shard(output_key, kept, payloads, put_bytes)
        _write_metrics(metrics_key, name, scored, keep_by_key, threshold, device, put_bytes)
        n_in, n_kept = len(scored), len(kept)
        shard_metrics.append(
            ShardMetric(
                shard=name,
                pairs_in=n_in,
                pairs_kept=n_kept,
                pairs_dropped=n_in - n_kept,
                mean_clip_score=round(
                    sum(p.score for p in scored) / n_in if n_in else 0.0, 4
                ),
                kept_mean_clip_score=round(
                    sum(p.score for p in kept) / n_kept if n_kept else 0.0, 4
                ),
                output_key=output_key,
                metrics_key=metrics_key,
            )
        )
        total_in += n_in
        total_kept += n_kept
        score_sum += sum(p.score for p in scored)

    dropped = total_in - total_kept
    stats = FilterStats(
        total_pairs_in=total_in,
        total_pairs_kept=total_kept,
        total_pairs_dropped=dropped,
        reduction_pct=round(100.0 * dropped / total_in, 2) if total_in else 0.0,
        mean_clip_score=round(score_sum / total_in, 4) if total_in else 0.0,
        clip_score_threshold=round(threshold, 4),
        device=device,
    )
    logger.info(
        "Filter run %s complete: kept %d/%d (%.1f%% reduction)",
        run.id,
        total_kept,
        total_in,
        stats.reduction_pct,
    )
    return run.model_copy(
        update={
            "status": RunStatus.completed,
            "stats": stats,
            "shard_metrics": shard_metrics,
            "source_shard_count": len(shards),
            "progress": RunProgress(
                shards_done=len(shards), shards_total=len(shards)
            ),
            "error": None,
            "updated_at": datetime.now(UTC),
        }
    )
