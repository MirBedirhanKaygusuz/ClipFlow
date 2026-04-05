"""Thumbnail endpoints — generate and serve video thumbnails."""

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.services.thumbnail import generate_thumbnail, generate_thumbnail_strip

router = APIRouter()
log = structlog.get_logger()


@router.post("/thumbnails/{file_id}")
async def create_thumbnail(file_id: str, timestamp: float | None = None):
    """Generate a thumbnail for an uploaded video.

    Args:
        file_id: The video file ID (from upload).
        timestamp: Optional specific timestamp. None = auto-detect best frame.

    Returns:
        Thumbnail metadata with URL to retrieve it.
    """
    video_path = Path(settings.storage_path) / f"{file_id}.mp4"
    if not video_path.exists():
        raise HTTPException(404, f"Video bulunamadı: {file_id}")

    thumb_path = await generate_thumbnail(
        str(video_path),
        timestamp=timestamp,
    )

    log.info("thumbnail_created", file_id=file_id)
    return {
        "file_id": file_id,
        "thumbnail_url": f"/api/v1/thumbnails/{file_id}",
        "path": thumb_path,
    }


@router.get("/thumbnails/{file_id}")
async def get_thumbnail(file_id: str):
    """Serve a generated thumbnail image.

    Returns the JPEG image directly.
    """
    thumb_path = Path(settings.storage_path) / "thumbnails" / f"{file_id}.jpg"
    if not thumb_path.exists():
        # Try to auto-generate
        video_path = Path(settings.storage_path) / f"{file_id}.mp4"
        if not video_path.exists():
            raise HTTPException(404, f"Thumbnail bulunamadı: {file_id}")

        await generate_thumbnail(str(video_path), str(thumb_path))

    return FileResponse(
        str(thumb_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/thumbnails/{file_id}/strip")
async def create_thumbnail_strip(file_id: str, count: int = 5):
    """Generate a strip of thumbnails evenly spaced through the video.

    Useful for timeline scrubbing in the iOS app.

    Args:
        file_id: The video file ID.
        count: Number of thumbnails (default 5, max 20).

    Returns:
        List of thumbnail URLs.
    """
    if count > 20:
        count = 20

    video_path = Path(settings.storage_path) / f"{file_id}.mp4"
    if not video_path.exists():
        raise HTTPException(404, f"Video bulunamadı: {file_id}")

    paths = await generate_thumbnail_strip(str(video_path), count=count)

    return {
        "file_id": file_id,
        "count": len(paths),
        "thumbnails": [
            f"/api/v1/thumbnails/{file_id}/strip/{i}"
            for i in range(len(paths))
        ],
    }


@router.get("/thumbnails/{file_id}/strip/{index}")
async def get_strip_thumbnail(file_id: str, index: int):
    """Serve a single thumbnail from a strip."""
    thumb_path = (
        Path(settings.storage_path) / "thumbnails" / file_id / f"frame_{index:03d}.jpg"
    )
    if not thumb_path.exists():
        raise HTTPException(404, f"Thumbnail bulunamadı: {file_id}/{index}")

    return FileResponse(str(thumb_path), media_type="image/jpeg")
