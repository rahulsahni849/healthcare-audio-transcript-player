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
    files = []
    for i, dur in enumerate(DURATIONS, start=1):
        f = rec_dir / "parts" / f"part-{i}.mp3"
        f.write_bytes(make_mp3())
        files.append(f)
        parts.append({"index": i, "file": f"parts/part-{i}.mp3", "duration": dur})

        words = []
        t = 0.0
        for j, word in enumerate(["alpha", "beta", "gamma", "delta"]):
            words.append({"word": word, "start": round(t, 3), "end": round(t + dur / 8, 3)})
            t += dur / 4
        (rec_dir / "transcripts" / f"part-{i}.json").write_text(
            json.dumps({"part": i, "words": words})
        )

    (data_dir / "recordings.json").write_text(
        json.dumps(
            {"recordings": [{"id": "test-rec", "title": "Test Rec", "parts": parts}]}
        )
    )

    monkeypatch.setattr(settings, "data_dir", data_dir)
    _load_manifest.cache_clear()
    with TestClient(create_app()) as c:
        yield c
    _load_manifest.cache_clear()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_recordings(client):
    data = client.get("/api/recordings").json()
    assert len(data) == 1
    rec = data[0]
    assert rec["id"] == "test-rec"
    assert rec["partCount"] == 3
    assert rec["totalDuration"] == pytest.approx(24.0)


def test_detail_offsets_are_cumulative(client):
    parts = client.get("/api/recordings/test-rec").json()["parts"]
    assert [p["start"] for p in parts] == [0.0, 10.0, 18.0]
    assert [p["end"] for p in parts] == [10.0, 18.0, 24.0]


def test_detail_not_found(client):
    r = client.get("/api/recordings/nope")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "RECORDING_NOT_FOUND"


def test_transcript_words_rebased_to_global_time(client):
    data = client.get("/api/recordings/test-rec/transcript").json()
    part2_first = next(w for w in data["words"] if w["part"] == 2)
    assert part2_first["start"] == pytest.approx(10.0, abs=0.01)
    part3_words = [w for w in data["words"] if w["part"] == 3]
    assert all(w["start"] >= 18.0 for w in part3_words)
    assert data["totalDuration"] == pytest.approx(24.0)


def test_audio_full_response(client):
    r = client.get("/api/recordings/test-rec/parts/1/audio")
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert "etag" in r.headers
    assert len(r.content) > 0


def test_audio_partial_content(client):
    r = client.get("/api/recordings/test-rec/parts/1/audio", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206
    assert r.headers["content-range"].startswith("bytes 0-99/")
    assert len(r.content) == 100


def test_audio_open_ended_range(client):
    full = client.get("/api/recordings/test-rec/parts/1/audio").content
    r = client.get("/api/recordings/test-rec/parts/1/audio", headers={"Range": "bytes=100-"})
    assert r.status_code == 206
    assert r.content == full[100:]


def test_audio_suffix_range(client):
    full = client.get("/api/recordings/test-rec/parts/1/audio").content
    r = client.get("/api/recordings/test-rec/parts/1/audio", headers={"Range": "bytes=-50"})
    assert r.status_code == 206
    assert r.content == full[-50:]


def test_audio_range_byte_accuracy(client):
    full = client.get("/api/recordings/test-rec/parts/1/audio").content
    r = client.get("/api/recordings/test-rec/parts/1/audio", headers={"Range": "bytes=256-511"})
    assert r.content == full[256:512]


def test_audio_unsatisfiable_range_416(client):
    r = client.get("/api/recordings/test-rec/parts/1/audio", headers={"Range": "bytes=99999999-"})
    assert r.status_code == 416
    assert r.headers["content-range"] == "bytes */%d" % len(
        client.get("/api/recordings/test-rec/parts/1/audio").content
    )


def test_audio_part_not_found(client):
    assert client.get("/api/recordings/test-rec/parts/99/audio").status_code == 404
