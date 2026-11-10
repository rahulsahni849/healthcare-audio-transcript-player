import json
from functools import lru_cache
from typing import Any

from app.core.config import settings


class ManifestError(Exception):
    """Raised when the manifest is missing or malformed."""


class RecordingNotFound(Exception):
    pass


class PartNotFound(Exception):
    pass


_last_mtime_ns: int | None = None


@lru_cache(maxsize=1)
def _load_manifest(cached_mtime_ns: int) -> dict[str, Any]:
    path = settings.manifest_path
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    _validate(data)
    return data


def _validate(data: Any) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("recordings"), list):
        raise ManifestError("manifest must contain a 'recordings' list")
    seen: set[str] = set()
    for rec in data["recordings"]:
        rec_id = rec.get("id")
        if not rec_id or rec_id in seen:
            raise ManifestError(f"invalid or duplicate recording id: {rec_id!r}")
        seen.add(rec_id)
        parts = rec.get("parts")
        if not isinstance(parts, list) or not parts:
            raise ManifestError(f"recording {rec_id} has no parts")
        for i, part in enumerate(parts, start=1):
            if part.get("index") != i:
                raise ManifestError(f"recording {rec_id}: part indices must be 1..N in order")
            if not (isinstance(part.get("duration"), (int, float)) and part["duration"] > 0):
                raise ManifestError(f"recording {rec_id} part {i}: invalid duration")
            if not part.get("file") or not (settings.recordings_dir / rec_id / part["file"]).is_file():
                raise ManifestError(f"recording {rec_id} part {i}: file missing on disk")


def get_manifest() -> dict[str, Any]:
    global _last_mtime_ns
    path = settings.manifest_path
    if not path.is_file():
        raise ManifestError(
            f"manifest not found at {path}. Run scripts/generate_demo_data.py first."
        )
    mtime_ns = path.stat().st_mtime_ns
    if _load_manifest.cache_info().currsize and _last_mtime_ns != mtime_ns:
        _load_manifest.cache_clear()
    _last_mtime_ns = mtime_ns
    return _load_manifest(mtime_ns)


def get_recording(recording_id: str) -> dict[str, Any]:
    for rec in get_manifest()["recordings"]:
        if rec["id"] == recording_id:
            return rec
    raise RecordingNotFound(recording_id)


def recording_dir(recording: dict[str, Any]):
    return settings.recordings_dir / recording["id"]


def get_part(recording: dict[str, Any], index: int) -> dict[str, Any]:
    for part in recording["parts"]:
        if part["index"] == index:
            return part
    raise PartNotFound(f"part {index} of {recording['id']}")


def part_file(recording: dict[str, Any], part: dict[str, Any]):
    base = recording_dir(recording).resolve()
    resolved = (base / part["file"]).resolve()
    if not resolved.is_relative_to(base):
        raise PartNotFound("invalid part path")
    return resolved
