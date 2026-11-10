import shutil
from pathlib import Path
from typing import Any

from app.services.manifest import part_file, recording_dir

COPY_CHUNK = 1024 * 1024


def merged_path(recording: dict[str, Any]) -> Path:
    return recording_dir(recording) / "merged.mp3"


def merged_filename(recording: dict[str, Any]) -> str:
    safe = "".join(c if c.isalnum() else "-" for c in recording["title"]).strip("-")
    return f"{safe or recording['id']}.mp3"


def is_stale(recording: dict[str, Any], merged: Path) -> bool:
    if not merged.is_file():
        return True
    merged_mtime = merged.stat().st_mtime
    for part in recording["parts"]:
        if part_file(recording, part).stat().st_mtime > merged_mtime:
            return True
    return False


def merge_recording(recording: dict[str, Any]) -> Path:
    """Concatenate all part files into one MP3 at <recording>/merged.mp3.

    Parts produced by the same encoder settings (CBR, same sample rate) concatenate
    into a continuous valid MP3 stream, so this is a plain byte copy.
    """
    out = merged_path(recording)
    if not is_stale(recording, out):
        return out
    tmp = out.with_name(out.name + ".tmp")
    with tmp.open("wb") as dst:
        for part in recording["parts"]:
            src_path = part_file(recording, part)
            with src_path.open("rb") as src:
                shutil.copyfileobj(src, dst, COPY_CHUNK)
    tmp.replace(out)
    return out
