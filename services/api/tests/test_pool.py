"""Pool Explorer tests. The B2 repo boundary is mocked; a real in-memory
WebDataset shard is built with Pillow (base dep) so parsing is exercised for
real without any network or ML stack."""

import io
import tarfile

import pytest
from PIL import Image

from app.service import pool as pool_service


def _make_shard() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for i in range(3):
            img = Image.new("RGB", (64, 64), (i * 40, 80, 200))
            jpg = io.BytesIO()
            img.save(jpg, format="JPEG")
            data = jpg.getvalue()
            info = tarfile.TarInfo(name=f"pair-{i}.jpg")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            caption = f"a photo number {i}".encode()
            tinfo = tarfile.TarInfo(name=f"pair-{i}.txt")
            tinfo.size = len(caption)
            tar.addfile(tinfo, io.BytesIO(caption))
    return buffer.getvalue()


@pytest.fixture
def mock_pool(monkeypatch):
    shard = _make_shard()
    monkeypatch.setattr(
        pool_service,
        "list_shards",
        lambda prefix: [{"key": f"{prefix}shard-0000.tar", "size": len(shard), "last_modified": 0}],
    )
    monkeypatch.setattr(pool_service, "get_object_bytes", lambda key: shard)
    monkeypatch.setattr(pool_service, "load_json", lambda key: None)
    return shard


async def test_list_pool_shards(client, mock_pool):
    resp = await client.get("/pool/shards?scope=pool")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["scope"] == "pool"
    assert body[0]["key"] == "pool/shard-0000.tar"


async def test_list_filtered_shards_extracts_run_id(client, mock_pool):
    resp = await client.get("/pool/shards?scope=filtered")
    assert resp.status_code == 200
    # list_shards mock echoes the prefix, so the key is filtered/shard-0000.tar
    assert resp.json()[0]["scope"] == "filtered"


async def test_bad_scope_400(client, mock_pool):
    assert (await client.get("/pool/shards?scope=bogus")).status_code == 400


async def test_open_shard_returns_pairs(client, mock_pool):
    resp = await client.get("/pool/shard?key=pool/shard-0000.tar")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pair_count"] == 3
    assert body["shown"] == 3
    first = body["pairs"][0]
    assert first["caption"].startswith("a photo number")
    assert first["thumbnail_data_url"].startswith("data:image/jpeg;base64,")
    # No metrics for a pool shard, so no score/kept.
    assert first["clip_score"] is None


async def test_open_out_of_scope_shard_400(client, mock_pool):
    assert (await client.get("/pool/shard?key=uploads/x.tar")).status_code == 400
