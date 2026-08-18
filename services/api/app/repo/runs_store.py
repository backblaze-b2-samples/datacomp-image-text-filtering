"""B2-backed persistence for Filter Runs and their artifacts.

The run manifest (`runs/<id>/manifest.json`) is the sole source of truth — there
is no database. Filtered shards land under `filtered/<id>/` and per-shard metrics
under `metrics/<id>/`. boto3/botocore stays confined to the repo layer (this
module reuses the cached S3 client from `b2_client`).
"""

import json

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache

RUNS_PREFIX = "runs/"
FILTERED_PREFIX = "filtered/"
METRICS_PREFIX = "metrics/"


def _manifest_key(run_id: str) -> str:
    return f"{RUNS_PREFIX}{run_id}/manifest.json"


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    """Write raw bytes to B2 (filtered shards, metrics JSON, manifests).

    Invalidates the shared listing cache so new objects show up in the
    (full-bucket) Bucket Explorer immediately. Raises RuntimeError on failure.
    """
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    _invalidate_list_cache()


def save_manifest(run_id: str, manifest: dict) -> None:
    body = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    put_bytes(_manifest_key(run_id), body, "application/json")


def load_manifest(run_id: str) -> dict | None:
    """Read and parse a run manifest. Returns None if it does not exist."""
    client = get_s3_client()
    try:
        response = client.get_object(
            Bucket=settings.b2_bucket_name, Key=_manifest_key(run_id)
        )
        return json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get manifest failed for '{run_id}': {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"B2 get manifest failed for '{run_id}': {e}") from e


def load_json(key: str) -> dict | None:
    """Read and parse an arbitrary JSON object (e.g. a per-shard metrics file)."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get JSON failed for '{key}': {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"B2 get JSON failed for '{key}': {e}") from e


def _list_keys(prefix: str) -> list[dict]:
    """Every object under `prefix` as {key, size, last_modified}. Not cached —
    run/pool prefixes are small and change per run."""
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                out.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return out


def list_shards(prefix: str) -> list[dict]:
    """List `.tar` shard objects under `prefix` (newest first)."""
    shards = [o for o in _list_keys(prefix) if o["key"].endswith(".tar")]
    shards.sort(key=lambda o: o["last_modified"], reverse=True)
    return shards


def list_manifests() -> list[dict]:
    """Load every run manifest under `runs/`."""
    manifests: list[dict] = []
    for obj in _list_keys(RUNS_PREFIX):
        if not obj["key"].endswith("/manifest.json"):
            continue
        run_id = obj["key"][len(RUNS_PREFIX) :].split("/", 1)[0]
        manifest = load_manifest(run_id)
        if manifest is not None:
            manifests.append(manifest)
    return manifests


def _delete_keys(keys: list[str]) -> None:
    if not keys:
        return
    client = get_s3_client()
    try:
        for start in range(0, len(keys), 1000):
            batch = keys[start : start + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 batch delete failed: {e}") from e
    _invalidate_list_cache()


def delete_run(run_id: str) -> None:
    """Delete a run manifest and, scoped to THIS run only, its
    `filtered/<id>/` and `metrics/<id>/` artifacts. Never touches the raw pool
    or any other run's prefixes."""
    keys = [_manifest_key(run_id)]
    keys += [o["key"] for o in _list_keys(f"{FILTERED_PREFIX}{run_id}/")]
    keys += [o["key"] for o in _list_keys(f"{METRICS_PREFIX}{run_id}/")]
    _delete_keys(keys)
