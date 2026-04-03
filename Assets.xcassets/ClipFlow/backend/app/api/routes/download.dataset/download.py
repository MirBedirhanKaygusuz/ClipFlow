"""Download endpoints — serve processed videos."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.storage import get_storage

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
    storage = get_storage()
    key = f"{file_id}.mp4"

    if not await storage.exists(key):
        raise HTTPException(status_code=404, detail=f"Dosya bulunamadı: {file_id}")

    file_path = await storage.get_path(key)

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=f"{file_id}.mp4",
        headers={"Content-Disposition": f'attachment; filename="{file_id}.mp4"'},
    )
