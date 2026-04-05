"""Waveform endpoints — audio visualization data for timeline UI."""

from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.config import settings
from app.services.waveform import generate_waveform

router = APIRouter()


@router.get("/waveform/{file_id}")
async def get_waveform(file_id: str, samples: int = 200):
    """Generate audio waveform data for a video or music file.

    Returns normalized amplitude samples (0.0-1.0) for rendering
    a waveform visualization in the iOS timeline.

    Args:
        file_id: The uploaded video or music file ID.
        samples: Number of waveform samples (default 200, max 1000).

    Returns:
        Waveform data with samples array, duration, and sample count.
    """
    if samples > 1000:
        samples = 1000
    if samples < 10:
        samples = 10

    # Check video storage first, then music
    video_path = Path(settings.storage_path) / f"{file_id}.mp4"
    if not video_path.exists():
        raise HTTPException(404, f"Dosya bulunamadı: {file_id}")

    result = await generate_waveform(str(video_path), samples=samples)

    return {
        "file_id": file_id,
        **result,
    }
