"""Download endpoints — serve processed videos."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings

router = APIRouter()


@router.get("/download/{file_id}")
async def download_file(file_id: str) -> FileResponse:
    """Download a processed video file.

    Args:
        file_id: The file identifier (typically job_id + suffix).

    Returns:
        FileResponse streaming the video file with Content-Disposition header.

    Raises:
        HTTPException: 404 if file not found.
    """
    file_path = Path(settings.storage_path) / f"{file_id}.mp4"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Dosya bulunamadı: {file_id}")

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=f"{file_id}.mp4",
        headers={"Content-Disposition": f'attachment; filename="{file_id}.mp4"'},
    )
