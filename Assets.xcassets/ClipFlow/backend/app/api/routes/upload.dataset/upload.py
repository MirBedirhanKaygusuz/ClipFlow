"""Upload endpoints."""

from fastapi import APIRouter, UploadFile, HTTPException
from uuid import uuid4
from pathlib import Path
import aiofiles

from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v"}


@router.post("/upload")
async def upload_file(file: UploadFile):
    """Upload a video file. Returns file_id for processing."""

    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Desteklenmeyen format: {ext}. Sadece MP4/MOV/M4V.")

    # Generate unique ID and save
    file_id = str(uuid4())
    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{file_id}{ext}"

    size = 0
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > settings.max_upload_size_mb * 1024 * 1024:
                await aiofiles.os.remove(file_path)
                raise HTTPException(413, f"Dosya çok büyük (maks {settings.max_upload_size_mb}MB)")
            await f.write(chunk)

    return {"file_id": file_id, "size_mb": round(size / 1024 / 1024, 1)}
