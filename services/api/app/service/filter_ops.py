"""Pure filtering helpers — no ML imports.

Kept ML-free on purpose: the torch/open_clip/webdataset stack lives ONLY in
`service/filtering.py`. These functions read WebDataset shards (stdlib tarfile),
decide keep/drop from already-computed scores, and guess image MIME types, so
both the filter engine and the Pool Explorer can reuse them without dragging in
the heavy stack.
"""

from __future__ import annotations

import io
import tarfile
from dataclasses import dataclass

from app.types.runs import FilterStrategy, RunConfig

_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}


@dataclass
class ScoredPair:
    """One image-text pair after CLIP scoring (built in filtering.py)."""

    key: str
    caption: str
    score: float
    width: int
    height: int
    n_tokens: int
    img_hash: str


def read_webdataset_pairs(shard_bytes: bytes) -> list[tuple[str, bytes, str]]:
    """Read `<key>.jpg` + `<key>.txt` pairs from a WebDataset `.tar` shard.

    Returns [(key, image_bytes, caption)] for every key that has both an image
    and a caption. Demo shards are small, so the whole shard is held in memory
    (documented demo-scale simplification; production streams via WebDataset's
    S3 reader).
    """
    images: dict[str, bytes] = {}
    captions: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(shard_bytes)) as tar:
        for member in tar.getmembers():
            if not member.isfile() or "." not in member.name:
                continue
            base, ext = member.name.rsplit(".", 1)
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            if ext.lower() in _IMAGE_EXTS:
                images[base] = data
            elif ext.lower() == "txt":
                captions[base] = data.decode("utf-8", "replace")
    return [
        (base, images[base], captions[base])
        for base in sorted(images)
        if base in captions
    ]


def count_tokens(caption: str) -> int:
    """Whitespace token count — the demo's stand-in for a real tokenizer when
    applying caption-length bounds (a text-based DataComp baseline knob)."""
    return len(caption.split())


def keep_threshold(scores: list[float], keep_fraction: float) -> float:
    """CLIP-score cutoff that keeps ~`keep_fraction` of pairs (highest scoring).

    keep_fraction=0.30 keeps the top 30% — DataComp's clip_score default.
    """
    if not scores:
        return 0.0
    ordered = sorted(scores)
    drop = round((1.0 - keep_fraction) * len(ordered))
    drop = min(max(drop, 0), len(ordered) - 1)
    return ordered[drop]


def apply_filters(
    pairs: list[ScoredPair], config: RunConfig
) -> tuple[list[bool], float]:
    """Decide keep/drop for every pair. Returns (keep_flags, score_threshold).

    Mirrors DataComp's baseline families:
      - clip_score:  keep the top-percentile pairs by CLIP score.
      - basic:       clip_score AND min resolution AND caption-length bounds.
      - image_based: min resolution only.
      - text_based:  caption-length bounds only.
    `dedup` additionally drops near-duplicate images (equal average-hash) when on.
    """
    uses_score = config.strategy in (FilterStrategy.clip_score, FilterStrategy.basic)
    threshold = (
        keep_threshold([p.score for p in pairs], config.clip_percentile)
        if uses_score
        else 0.0
    )
    seen: set[str] = set()
    flags: list[bool] = []
    for pair in pairs:
        res_ok = min(pair.width, pair.height) >= config.min_resolution
        caption_ok = (
            config.caption_min_tokens <= pair.n_tokens <= config.caption_max_tokens
        )
        score_ok = pair.score >= threshold
        if config.strategy == FilterStrategy.clip_score:
            keep = score_ok
        elif config.strategy == FilterStrategy.basic:
            keep = score_ok and res_ok and caption_ok
        elif config.strategy == FilterStrategy.image_based:
            keep = res_ok
        else:  # text_based
            keep = caption_ok
        if keep and config.dedup:
            if pair.img_hash in seen:
                keep = False
            else:
                seen.add(pair.img_hash)
        flags.append(keep)
    return flags, threshold


def guess_image_mime(data: bytes) -> str:
    """Best-effort image MIME from magic bytes, for building data URLs."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"
