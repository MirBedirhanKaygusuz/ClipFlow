"""Upload endpoints."""

from fastapi import APIRouter, Request, HTTPException, Header
from uuid import uuid4
from pathlib import Path
from typing import Optional
import aiofiles

from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v"}


@router.post("/upload")
async def upload_file(
    request: Request,
    x_filename: Optional[str] = Header(default="video.mp4"),
):
    """Upload a video file as raw binary. Returns file_id for processing."""

    ext = Path(x_filename or "video.mp4").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".mp4"  # safe fallback

    file_id = str(uuid4())
    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{file_id}{ext}"

    size = 0
    async with aiofiles.open(file_path, "wb") as f:
        async for chunk in request.stream():
            size += len(chunk)
            if size > settings.max_upload_size_mb * 1024 * 1024:
                await aiofiles.os.remove(file_path)
                raise HTTPException(413, f"Dosya çok büyük (maks {settings.max_upload_size_mb}MB)")
            await f.write(chunk)

    return {"file_id": file_id, "size_mb": round(size / 1024 / 1024, 1)}
