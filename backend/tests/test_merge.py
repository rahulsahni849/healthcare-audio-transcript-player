import time


def part_bytes(client) -> list[bytes]:
    return [
        client.get(f"/api/recordings/test-rec/parts/{i}/audio").content for i in (1, 2, 3)
    ]


def test_merge_returns_metadata(client):
    r = client.post("/api/recordings/test-rec/merge")
    assert r.status_code == 200
    body = r.json()
    expected = sum(len(b) for b in part_bytes(client))
    assert body["size"] == expected
    assert body["filename"] == "Test-Rec.mp3"
    assert body["partCount"] == 3


def test_merge_output_is_byte_concatenation(client):
    client.post("/api/recordings/test-rec/merge")
    merged = (client.get("/api/recordings/test-rec").json(),)
    import pathlib

    from app.core.config import settings

    path = pathlib.Path(settings.data_dir) / "recordings" / "test-rec" / "merged.mp3"
    assert path.read_bytes() == b"".join(part_bytes(client))
    assert merged is not None


def test_merge_is_cached_until_part_changes(client):
    import pathlib

    from app.core.config import settings

    path = pathlib.Path(settings.data_dir) / "recordings" / "test-rec" / "merged.mp3"
    client.post("/api/recordings/test-rec/merge")
    first_mtime = path.stat().st_mtime_ns

    time.sleep(0.01)
    client.post("/api/recordings/test-rec/merge")
    assert path.stat().st_mtime_ns == first_mtime

    time.sleep(0.01)
    part1 = path.parent / "parts" / "part-1.mp3"
    part1.write_bytes(part1.read_bytes())
    client.post("/api/recordings/test-rec/merge")
    assert path.stat().st_mtime_ns != first_mtime


def test_download_serves_attachment(client):
    r = client.get("/api/recordings/test-rec/download")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert "attachment" in r.headers["content-disposition"]
    assert "Test-Rec.mp3" in r.headers["content-disposition"]
    assert r.content == b"".join(part_bytes(client))


def test_download_builds_if_merge_never_called(client):
    r = client.get("/api/recordings/test-rec/download")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_merge_404(client):
    r = client.post("/api/recordings/nope/merge")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "RECORDING_NOT_FOUND"


def test_download_404(client):
    assert client.get("/api/recordings/nope/download").status_code == 404
