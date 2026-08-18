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


async def test_run_pairs_surfaces_dropped_scores(client, mem_store, monkeypatch):
    """The per-pair endpoint exposes DROPPED pairs and their low scores — the
    filtered .tar holds only kept pairs, so this reads the run's metrics JSON."""
    created = (await client.post("/runs", json={"name": "scored"})).json()
    rid = created["id"]
    stored = mem_store[rid]
    stored["status"] = "completed"
    stored["shard_metrics"] = [
        {
            "shard": "shard-0000.tar",
            "pairs_in": 2,
            "pairs_kept": 1,
            "pairs_dropped": 1,
            "mean_clip_score": 0.2,
            "kept_mean_clip_score": 0.3,
            "output_key": f"filtered/{rid}/shard-0000.tar",
            "metrics_key": f"metrics/{rid}/shard-0000.json",
        }
    ]
    stored["stats"] = {
        "total_pairs_in": 2,
        "total_pairs_kept": 1,
        "total_pairs_dropped": 1,
        "reduction_pct": 50.0,
        "mean_clip_score": 0.2,
        "clip_score_threshold": 0.25,
        "device": "cpu",
    }
    doc = {
        "shard": "shard-0000.tar",
        "clip_score_threshold": 0.25,
        "device": "cpu",
        "pair_count": 2,
        "pairs": [
            {"key": "a", "caption": "a kept pair", "clip_score": 0.3, "kept": True},
            {"key": "b", "caption": "a dropped pair", "clip_score": 0.1, "kept": False},
        ],
    }
    monkeypatch.setattr(runs_service, "load_json", lambda key: doc)

    resp = await client.get(f"/runs/{rid}/pairs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pair_count"] == 2
    assert body["clip_score_threshold"] == 0.25
    # Sorted by score descending: kept 0.3 first.
    assert body["pairs"][0]["kept"] is True
    dropped = [p for p in body["pairs"] if not p["kept"]]
    assert len(dropped) == 1
    assert dropped[0]["clip_score"] == 0.1
    assert dropped[0]["caption"] == "a dropped pair"


async def test_run_pairs_missing_run_404(client, mem_store):
    assert (await client.get("/runs/nope/pairs")).status_code == 404


async def test_start_run_seeds_progress_total(client, mem_store, monkeypatch):
    """start_run seeds shards_total from the pool listing so the progress bar
    has a denominator from the very first poll."""
    monkeypatch.setattr(
        runs_service,
        "list_shards",
        lambda prefix: [
            {"key": "pool/a.tar", "size": 1, "last_modified": 0},
            {"key": "pool/b.tar", "size": 1, "last_modified": 0},
        ],
    )
    created = (await client.post("/runs", json={"name": "go"})).json()
    resp = await client.post(f"/runs/{created['id']}/run")
    assert resp.status_code == 200
    assert resp.json()["progress"] == {"shards_done": 0, "shards_total": 2}


def test_execute_run_reports_progress(mem_store, monkeypatch):
    """execute_run injects an on_progress callback that persists mid-run
    advancement, so a poll during pass 1 sees the determinate bar move."""
    from app.types.runs import RunCreateRequest, RunStatus

    seen: list[dict] = []

    def fake_run_filter(run, gb, pb, ls, on_progress=None):
        assert on_progress is not None
        on_progress(1, 2)
        seen.append(dict(mem_store[run.id]["progress"]))
        on_progress(2, 2)
        return run.model_copy(update={"status": RunStatus.completed})

    monkeypatch.setattr(filtering, "run_filter", fake_run_filter)
    run = runs_service.create_run(RunCreateRequest(name="prog"))
    runs_service.execute_run(run.id)
    assert seen[0] == {"shards_done": 1, "shards_total": 2}
    assert mem_store[run.id]["status"] == "completed"
    assert mem_store[run.id]["progress"]["shards_done"] == 2


async def test_run_stats_empty(client, mem_store):
    resp = await client.get("/runs/stats")
    assert resp.status_code == 200
    assert resp.json()["total_runs"] == 0


async def test_source_prefixes_defaults_to_pool(client, mem_store):
    resp = await client.get("/runs/source-prefixes")
    assert resp.status_code == 200
    assert resp.json() == [{"prefix": "pool/", "shard_count": 0}]
