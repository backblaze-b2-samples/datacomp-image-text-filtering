"""Filter Run lifecycle tests. The repo (B2 manifest) boundary is mocked with an
in-memory store, so these are hermetic — no network, no ML stack."""

import pytest

from app.service import filtering
from app.service import runs as runs_service


@pytest.fixture
def mem_store(monkeypatch):
    """Replace the B2-backed manifest store with an in-memory dict, and stub the
    CLIP engine so a run's background task is deterministic and fast whether or
    not the ML stack happens to be installed (CI runs a base venv without it)."""
    store: dict[str, dict] = {}

    monkeypatch.setattr(runs_service, "save_manifest", lambda rid, m: store.__setitem__(rid, m))
    monkeypatch.setattr(runs_service, "load_manifest", lambda rid: store.get(rid))
    monkeypatch.setattr(runs_service, "list_manifests", lambda: list(store.values()))
    monkeypatch.setattr(runs_service, "_repo_delete_run", lambda rid: store.pop(rid, None))
    monkeypatch.setattr(runs_service, "list_shards", lambda prefix: [])

    def _unavailable(*_a, **_k):
        raise filtering.FilterEngineUnavailableError(filtering.ML_HINT)

    monkeypatch.setattr(filtering, "run_filter", _unavailable)
    return store


async def test_create_run_defaults_to_pending(client, mem_store):
    resp = await client.post("/runs", json={"name": "my first run"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["config"]["name"] == "my first run"
    assert body["config"]["strategy"] == "clip_score"
    assert body["config"]["clip_percentile"] == 0.30
    assert body["output_prefix"] == f"filtered/{body['id']}/"


async def test_create_run_uses_selectors(client, mem_store):
    resp = await client.post(
        "/runs",
        json={"name": "vit-l run", "clip_model": "ViT-L-14", "strategy": "basic"},
    )
    assert resp.status_code == 200
    assert resp.json()["config"]["clip_model"] == "ViT-L-14"


async def test_create_run_rejects_bad_model(client, mem_store):
    resp = await client.post("/runs", json={"name": "x", "clip_model": "nope"})
    assert resp.status_code == 422


async def test_get_and_list_runs(client, mem_store):
    created = (await client.post("/runs", json={"name": "r1"})).json()
    got = await client.get(f"/runs/{created['id']}")
    assert got.status_code == 200
    listed = await client.get("/runs")
    assert listed.status_code == 200
    assert any(r["id"] == created["id"] for r in listed.json())


async def test_get_missing_run_404(client, mem_store):
    assert (await client.get("/runs/deadbeef")).status_code == 404


async def test_update_pending_run(client, mem_store):
    created = (await client.post("/runs", json={"name": "editable"})).json()
    resp = await client.put(
        f"/runs/{created['id']}",
        json={"name": "editable", "clip_percentile": 0.5, "strategy": "image_based"},
    )
    assert resp.status_code == 200
    assert resp.json()["config"]["clip_percentile"] == 0.5


async def test_update_completed_run_conflict(client, mem_store):
    created = (await client.post("/runs", json={"name": "done"})).json()
    mem_store[created["id"]]["status"] = "completed"
    resp = await client.put(f"/runs/{created['id']}", json={"name": "done"})
    assert resp.status_code == 409


async def test_delete_run(client, mem_store):
    created = (await client.post("/runs", json={"name": "trash"})).json()
    resp = await client.delete(f"/runs/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True, "id": created["id"]}
    assert (await client.get(f"/runs/{created['id']}")).status_code == 404


async def test_delete_missing_run_404(client, mem_store):
    assert (await client.delete("/runs/nope")).status_code == 404


async def test_start_run_returns_running(client, mem_store):
    created = (await client.post("/runs", json={"name": "go"})).json()
    resp = await client.post(f"/runs/{created['id']}/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_execute_run_persists_failed_on_engine_error(mem_store):
    """The dep-split guard: a FilterEngineUnavailableError (missing ML stack in
    the base venv, or an empty pool) is persisted as `failed` with an actionable
    message — the engine never crashes the process and the POST never 500s."""
    from app.types.runs import RunCreateRequest

    run = runs_service.create_run(RunCreateRequest(name="no-ml"))
    runs_service.execute_run(run.id)
    stored = mem_store[run.id]
    assert stored["status"] == "failed"
    assert "requirements-ml.txt" in stored["error"]


async def test_run_stats_empty(client, mem_store):
    resp = await client.get("/runs/stats")
    assert resp.status_code == 200
    assert resp.json()["total_runs"] == 0


async def test_source_prefixes_defaults_to_pool(client, mem_store):
    resp = await client.get("/runs/source-prefixes")
    assert resp.status_code == 200
    assert resp.json() == [{"prefix": "pool/", "shard_count": 0}]
