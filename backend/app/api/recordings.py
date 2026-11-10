from fastapi import APIRouter, HTTPException

from app.models.schemas import RecordingDetail, RecordingSummary
from app.services import manifest as manifest_svc
from app.services import transcript as transcript_svc
from app.services.manifest import ManifestError, RecordingNotFound

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("", response_model=list[RecordingSummary])
def list_recordings():
    out = []
    for rec in manifest_svc.get_manifest()["recordings"]:
        total = sum(p["duration"] for p in rec["parts"])
        out.append(
            RecordingSummary(
                id=rec["id"], title=rec["title"], part_count=len(rec["parts"]), total_duration=total
            )
        )
    return out


@router.get("/{recording_id}", response_model=RecordingDetail)
def recording_detail(recording_id: str):
    try:
        rec = manifest_svc.get_recording(recording_id)
    except RecordingNotFound:
        raise HTTPException(404, {"code": "RECORDING_NOT_FOUND", "message": recording_id})
    offset = 0.0
    parts = []
    for part in rec["parts"]:
        duration = float(part["duration"])
        parts.append(
            {"index": part["index"], "duration": duration, "start": offset, "end": offset + duration}
        )
        offset += duration
    return RecordingDetail(id=rec["id"], title=rec["title"], parts=parts, total_duration=offset)


@router.get("/{recording_id}/transcript")
def recording_transcript(recording_id: str):
    try:
        rec = manifest_svc.get_recording(recording_id)
    except RecordingNotFound:
        raise HTTPException(404, {"code": "RECORDING_NOT_FOUND", "message": recording_id})
    try:
        return transcript_svc.merge_transcript(rec)
    except ManifestError as e:
        raise HTTPException(500, {"code": "TRANSCRIPT_ERROR", "message": str(e)})
