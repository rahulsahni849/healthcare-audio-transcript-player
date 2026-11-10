import json
from typing import Any

from app.core.config import settings
from app.services.manifest import recording_dir

from .manifest import ManifestError


def load_part_transcript(recording: dict[str, Any], part: dict[str, Any]) -> dict[str, Any]:
    path = recording_dir(recording) / "transcripts" / f"part-{part['index']}.json"
    if not path.is_file():
        raise ManifestError(f"transcript missing for {recording['id']} part {part['index']}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("words"), list):
        raise ManifestError(f"transcript {path.name} missing 'words' list")
    return data


def merge_transcript(recording: dict[str, Any]) -> dict[str, Any]:
    offset = 0.0
    parts_out: list[dict[str, Any]] = []
    words_out: list[dict[str, Any]] = []

    for part in recording["parts"]:
        duration = float(part["duration"])
        data = load_part_transcript(recording, part)
        for w in data["words"]:
            start, end = float(w["start"]), float(w["end"])
            if end <= start:
                continue
            words_out.append(
                {
                    "word": str(w["word"]),
                    "start": round(offset + start, 3),
                    "end": round(offset + end, 3),
                    "part": part["index"],
                }
            )
        parts_out.append(
            {
                "index": part["index"],
                "duration": duration,
                "start": round(offset, 3),
                "end": round(offset + duration, 3),
            }
        )
        offset += duration

    words_out.sort(key=lambda w: w["start"])
    return {
        "recordingId": recording["id"],
        "totalDuration": round(offset, 3),
        "parts": parts_out,
        "words": words_out,
    }
