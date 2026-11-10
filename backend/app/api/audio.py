from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.services import manifest as manifest_svc
from app.services import media as media_svc
from app.services.manifest import PartNotFound, RecordingNotFound

router = APIRouter(prefix="/recordings/{recording_id}/parts/{part_index}", tags=["audio"])


def _audio_response(recording_id: str, part_index: int, range_header: str | None) -> StreamingResponse:
    try:
        rec = manifest_svc.get_recording(recording_id)
    except RecordingNotFound:
        raise HTTPException(404, {"code": "RECORDING_NOT_FOUND", "message": recording_id})
    try:
        part = manifest_svc.get_part(rec, part_index)
    except PartNotFound:
        raise HTTPException(404, {"code": "PART_NOT_FOUND", "message": f"part {part_index}"})

    path = manifest_svc.part_file(rec, part)
    file_size = path.stat().st_size

    try:
        rng = media_svc.parse_range(range_header, file_size)
    except media_svc.UnsatisfiableRange:
        raise HTTPException(
            416,
            {"code": "RANGE_NOT_SATISFIABLE", "message": f"file size {file_size}"},
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    status = 206 if rng is not None else 200
    content_range = f"bytes {rng.start}-{rng.end}/{file_size}" if rng else None

    headers = {
        "Accept-Ranges": "bytes",
        "ETag": media_svc.etag_for(path),
        "Cache-Control": "public, max-age=3600",
    }
    if content_range:
        headers["Content-Range"] = content_range

    return StreamingResponse(
        media_svc.file_chunks(path, rng),
        status_code=status,
        media_type="audio/mpeg",
        headers=headers,
    )


@router.get("/audio")
def stream_audio(recording_id: str, part_index: int, range: str | None = Header(default=None)):
    return _audio_response(recording_id, part_index, range)


@router.head("/audio")
def stream_audio_head(recording_id: str, part_index: int, range: str | None = Header(default=None)):
    return _audio_response(recording_id, part_index, range)
