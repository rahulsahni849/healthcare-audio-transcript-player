import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from app.core.config import settings

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class UnsatisfiableRange(Exception):
    def __init__(self, file_size: int):
        self.file_size = file_size


@dataclass(frozen=True)
class ByteRange:
    start: int
    end: int  # inclusive

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def parse_range(header: str | None, file_size: int) -> ByteRange | None:
    """Parse an HTTP Range header. Returns None for a full (200) response.

    Raises UnsatisfiableRange when the range cannot be served (-> 416).
    """
    if file_size <= 0:
        raise UnsatisfiableRange(file_size)
    if not header:
        return None
    m = _RANGE_RE.match(header.strip())
    if not m:
        return None
    start_s, end_s = m.groups()
    if start_s == "" and end_s == "":
        return None
    if start_s == "":
        # suffix range: bytes=-N -> last N bytes
        n = int(end_s)
        if n == 0:
            raise UnsatisfiableRange(file_size)
        length = min(n, file_size)
        return ByteRange(file_size - length, file_size - 1)
    start = int(start_s)
    if start >= file_size:
        raise UnsatisfiableRange(file_size)
    end = int(end_s) if end_s else file_size - 1
    return ByteRange(start, min(end, file_size - 1))


def etag_for(path: Path) -> str:
    stat = path.stat()
    return f'"{stat.st_size:x}-{int(stat.st_mtime):x}"'


def file_chunks(path: Path, rng: ByteRange | None = None) -> Iterator[bytes]:
    start = rng.start if rng else 0
    end = rng.end if rng else path.stat().st_size - 1
    remaining = end - start + 1
    with path.open("rb") as f:
        f.seek(start)
        while remaining > 0:
            chunk = f.read(min(settings.chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
