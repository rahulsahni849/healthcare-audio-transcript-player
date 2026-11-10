"""Scan backend/data/recordings/* and (re)write recordings.json with probed durations.

Usage: python backend/scripts/build_manifest.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402


def probe_duration(path: Path) -> float:
    from mutagen.mp3 import MP3

    return round(MP3(str(path)).info.length, 3)


def _derive_title(recording_id: str) -> str:
    return recording_id.replace("-", " ").replace("_", " ").title()


def build_manifest() -> None:
    recordings_dir = settings.recordings_dir
    if not recordings_dir.is_dir():
        raise SystemExit(f"no recordings directory at {recordings_dir}")

    existing_titles: dict[str, str] = {}
    if settings.manifest_path.is_file():
        try:
            prev = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
            existing_titles = {r["id"]: r.get("title", "") for r in prev["recordings"]}
        except Exception:
            pass

    recordings = []
    for rec_dir in sorted(p for p in recordings_dir.iterdir() if p.is_dir()):
        parts_dir = rec_dir / "parts"
        if not parts_dir.is_dir():
            continue
        files = sorted(
            parts_dir.glob("part-*.mp3"),
            key=lambda p: int(p.stem.split("-")[1]),
        )
        if not files:
            continue
        parts = [
            {
                "index": int(p.stem.split("-")[1]),
                "file": f"parts/{p.name}",
                "duration": probe_duration(p),
            }
            for p in files
        ]
        recordings.append(
            {
                "id": rec_dir.name,
                "title": existing_titles.get(rec_dir.name) or _derive_title(rec_dir.name),
                "parts": parts,
            }
        )

    if not recordings:
        raise SystemExit("no recordings with part-*.mp3 files found")

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.manifest_path.write_text(
        json.dumps({"recordings": recordings}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {settings.manifest_path} ({len(recordings)} recordings)")


if __name__ == "__main__":
    build_manifest()
