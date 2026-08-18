"""Seed a small SYNTHETIC, KEYLESS, DISTINGUISHABLE image-text pool into B2.

CLIP-score filtering is a semantic/alignment feature, so a pure-noise pool would
never exercise it. This generates a few dozen synthetic image-text pairs across
clearly distinct visual categories (colored geometric shapes drawn with Pillow),
pairing MOST with a MATCHING caption (high CLIP score -> kept) and a controlled
subset with a DELIBERATELY MISMATCHED caption (low CLIP score -> dropped). CLIP
percentile filtering then visibly separates aligned from misaligned pairs.

No download, no license review, no second API key — only your B2 credentials.
Packs pairs into WebDataset `.tar` shards (`<key>.jpg` + `<key>.txt`) under the
`pool/` prefix.

Usage (from the repo root, after `pnpm run setup`):
    services/api/.venv/bin/python services/api/scripts/seed_pool.py
    services/api/.venv/bin/python services/api/scripts/seed_pool.py --pairs 96 --shard-size 24
"""

from __future__ import annotations

import argparse
import io
import random
import sys
import tarfile
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from PIL import Image, ImageDraw  # noqa: E402

from app.config import settings  # noqa: E402
from app.repo import put_bytes  # noqa: E402

# (shape, color name, RGB). Captions are built from the shape + color so a
# matching caption aligns and a swapped one clearly does not.
CATEGORIES = [
    ("circle", "red", (220, 40, 40)),
    ("square", "blue", (40, 90, 220)),
    ("triangle", "green", (40, 180, 80)),
    ("star", "yellow", (235, 200, 40)),
    ("circle", "purple", (150, 60, 200)),
    ("square", "orange", (240, 140, 40)),
]

IMG_SIZE = 128
BG = (238, 238, 240)


def out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _draw_shape(draw: ImageDraw.ImageDraw, shape: str, color, rng: random.Random) -> None:
    pad = rng.randint(12, 26)
    box = (pad, pad, IMG_SIZE - pad, IMG_SIZE - pad)
    if shape == "circle":
        draw.ellipse(box, fill=color)
    elif shape == "square":
        draw.rectangle(box, fill=color)
    elif shape == "triangle":
        draw.polygon(
            [(IMG_SIZE // 2, pad), (pad, IMG_SIZE - pad), (IMG_SIZE - pad, IMG_SIZE - pad)],
            fill=color,
        )
    elif shape == "star":
        cx, cy, r = IMG_SIZE // 2, IMG_SIZE // 2, (IMG_SIZE - 2 * pad) // 2
        points = []
        for i in range(10):
            angle = i * 36 - 90
            radius = r if i % 2 == 0 else r // 2
            from math import cos, radians, sin

            points.append((cx + radius * cos(radians(angle)), cy + radius * sin(radians(angle))))
        draw.polygon(points, fill=color)


def _render(shape: str, color, rng: random.Random) -> bytes:
    """Render one 128x128 JPEG with light jitter so images aren't byte-identical
    (keeps average-hash dedup from collapsing a whole category to one pair)."""
    image = Image.new("RGB", (IMG_SIZE, IMG_SIZE), BG)
    draw = ImageDraw.Draw(image)
    # A little background texture, then the shape.
    for _ in range(rng.randint(0, 3)):
        x0, y0 = rng.randint(0, IMG_SIZE), rng.randint(0, IMG_SIZE)
        draw.rectangle([x0, y0, x0 + 10, y0 + 10], fill=(210, 210, 214))
    _draw_shape(draw, shape, color, rng)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _caption(shape: str, color: str) -> str:
    return f"a photo of a {color} {shape}"


def _add(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def _build_shard(pairs: list[tuple[str, bytes, str]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for key, jpg, caption in pairs:
            _add(tar, f"{key}.jpg", jpg)
            _add(tar, f"{key}.txt", caption.encode("utf-8"))
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=48, help="Total image-text pairs")
    parser.add_argument("--shard-size", type=int, default=24, help="Pairs per shard")
    parser.add_argument(
        "--mismatch-rate",
        type=float,
        default=0.3,
        help="Fraction given a deliberately mismatched caption (low CLIP score)",
    )
    parser.add_argument("--seed", type=int, default=7, help="Deterministic RNG seed")
    args = parser.parse_args()

    if not settings.b2_bucket_name or not settings.b2_region:
        out("B2 is not configured — set B2_* values in .env first (see .env.example).")
        return 2

    rng = random.Random(args.seed)
    matched = mismatched = 0
    shard_pairs: list[tuple[str, bytes, str]] = []
    shard_index = 0
    uploaded = 0

    def flush(shard_i: int, pairs: list[tuple[str, bytes, str]]) -> None:
        nonlocal uploaded
        if not pairs:
            return
        key = f"pool/shard-{shard_i:04d}.tar"
        put_bytes(key, _build_shard(pairs), "application/x-tar")
        uploaded += 1
        out(f"  uploaded {key} ({len(pairs)} pairs)")

    for i in range(args.pairs):
        shape, color, rgb = CATEGORIES[i % len(CATEGORIES)]
        jpg = _render(shape, rgb, rng)
        if rng.random() < args.mismatch_rate:
            # Deliberately mislabel with a different category's caption.
            other_shape, other_color, _ = rng.choice(
                [c for c in CATEGORIES if (c[0], c[1]) != (shape, color)]
            )
            caption = _caption(other_shape, other_color)
            mismatched += 1
        else:
            caption = _caption(shape, color)
            matched += 1
        key = f"shard-{shard_index:04d}-{len(shard_pairs):04d}"
        shard_pairs.append((key, jpg, caption))
        if len(shard_pairs) >= args.shard_size:
            flush(shard_index, shard_pairs)
            shard_index += 1
            shard_pairs = []
    flush(shard_index, shard_pairs)

    out(
        f"Seeded {args.pairs} pairs ({matched} matched, {mismatched} mismatched) "
        f"into {uploaded} shard(s) under pool/ in bucket {settings.b2_bucket_name}."
    )
    out("Now create and run a Filter Run in the UI (or via the API).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
