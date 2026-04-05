"""Video validation endpoints — check video before processing."""

import structlog
from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.config import settings
from app.services.video_validator import validate_video, suggest_splits

router = APIRouter()
log = structlog.get_logger()


@router.get("/validate/{file_id}")
async def validate_uploaded_video(file_id: str):
    """Validate an uploaded video and return metadata.

    Returns video info (duration, resolution, codec, fps) along with
    any errors or warnings (e.g., too long for Reels, no audio).

    Args:
        file_id: The uploaded video file ID.

    Returns:
        Validation result with info, errors, and warnings.
    """
    video_path = Path(settings.storage_path) / f"{file_id}.mp4"
    if not video_path.exists():
        raise HTTPException(404, f"Video bulunamadı: {file_id}")

    result = await validate_video(str(video_path))

    response = {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
    }

    if result.info:
        response["info"] = {
            "duration": result.info.duration,
            "width": result.info.width,
            "height": result.info.height,
            "video_codec": result.info.video_codec,
            "audio_codec": result.info.audio_codec,
            "fps": result.info.fps,
            "bitrate_kbps": result.info.bitrate,
            "file_size_mb": result.info.file_size_mb,
            "has_audio": result.info.has_audio,
            "rotation": result.info.rotation,
        }

    return response


@router.get("/validate/{file_id}/splits")
async def get_split_suggestions(file_id: str, max_duration: float = 90.0):
    """Suggest optimal split points for a long video.

    Uses scene detection to find natural cut points so splits happen
    at scene boundaries rather than mid-scene.

    Args:
        file_id: The uploaded video file ID.
        max_duration: Maximum seconds per segment (default 90 for Reels).

    Returns:
        List of suggested segments with start/end times.
    """
    video_path = Path(settings.storage_path) / f"{file_id}.mp4"
    if not video_path.exists():
        raise HTTPException(404, f"Video bulunamadı: {file_id}")

    if max_duration < 10:
        raise HTTPException(400, "Minimum segment süresi 10 saniye.")

    segments = await suggest_splits(str(video_path), max_duration=max_duration)

    return {
        "file_id": file_id,
        "needs_split": len(segments) > 1,
        "segments": segments,
    }
