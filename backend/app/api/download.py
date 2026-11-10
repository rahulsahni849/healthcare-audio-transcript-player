from fastapi import APIRouter, HTTPException

from fastapi.responses import FileResponse

from app.services import manifest as manifest_svc
from app.services import merge as merge_svc
from app.services.manifest import RecordingNotFound

router = APIRouter(prefix="/recordings/{recording_id}", tags=["download"])


@router.post("/merge")
def merge_recording(recording_id: str):
    try:
        rec = manifest_svc.get_recording(recording_id)
    except RecordingNotFound:
        raise HTTPException(404, {"code": "RECORDING_NOT_FOUND", "message": recording_id})
    path = merge_svc.merge_recording(rec)
    return {
        "filename": merge_svc.merged_filename(rec),
        "size": path.stat().st_size,
        "partCount": len(rec["parts"]),
    }


@router.get("/download")
def download_recording(recording_id: str):
    try:
        rec = manifest_svc.get_recording(recording_id)
    except RecordingNotFound:
        raise HTTPException(404, {"code": "RECORDING_NOT_FOUND", "message": recording_id})
    path = merge_svc.merge_recording(rec)
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename=merge_svc.merged_filename(rec),
        headers={
            "Cache-Control": "no-cache",
            "ETag": f'"{path.stat().st_size:x}-{int(path.stat().st_mtime):x}"',
        },
    )
