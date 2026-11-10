import json
import math

import lameenc
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app
from app.services.manifest import _load_manifest


def make_mp3(seconds: float = 0.5, freq: int = 440) -> bytes:
    rate = 22050
    n = int(rate * seconds)
    pcm = b"".join(
        int(12000 * math.sin(2 * math.pi * freq * i / rate)).to_bytes(2, "little", signed=True)
        for i in range(n)
    )
    enc = lameenc.Encoder()
    enc.set_bit_rate(128)
    enc.set_in_sample_rate(rate)
    enc.set_channels(1)
    enc.set_quality(5)
    return bytes(enc.encode(pcm)) + bytes(enc.flush())


DURATIONS = [10.0, 8.0, 6.0]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    rec_dir = data_dir / "recordings" / "test-rec"
    (rec_dir / "parts").mkdir(parents=True)
    (rec_dir / "transcripts").mkdir(parents=True)

    parts = []
    for i, dur in enumerate(DURATIONS, start=1):
        f = rec_dir / "parts" / f"part-{i}.mp3"
        f.write_bytes(make_mp3())
        parts.append({"index": i, "file": f"parts/part-{i}.mp3", "duration": dur})

        words = []
        t = 0.0
        for word in ["alpha", "beta", "gamma", "delta"]:
            words.append({"word": word, "start": round(t, 3), "end": round(t + dur / 8, 3)})
            t += dur / 4
        (rec_dir / "transcripts" / f"part-{i}.json").write_text(
            json.dumps({"part": i, "words": words})
        )

    (data_dir / "recordings.json").write_text(
        json.dumps({"recordings": [{"id": "test-rec", "title": "Test Rec", "parts": parts}]})
    )

    monkeypatch.setattr(settings, "data_dir", data_dir)
    _load_manifest.cache_clear()
    with TestClient(create_app()) as c:
        yield c
    _load_manifest.cache_clear()
