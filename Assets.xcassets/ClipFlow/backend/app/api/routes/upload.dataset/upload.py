"""Upload endpoints."""

from fastapi import APIRouter, UploadFile, HTTPException, Request
from uuid import uuid4
from pathlib import Path
import aiofiles
import structlog

from app.config import settings
from app.services.storage import get_storage
from app.services.thumbnail import generate_thumbnail

router = APIRouter()
log = structlog.get_logger()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v"}


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile | None = None):
    """Upload a video file. Supports both multipart/form-data and raw binary.

    - Multipart: Standard file upload with 'file' field.
    - Raw binary: application/octet-stream with X-Filename header (iOS streaming).
    """
    content_type = request.headers.get("content-type", "")
    file_id = str(uuid4())
    storage = get_storage()

    # Temporary local path for initial write (always needed for streaming)
    tmp_dir = Path(settings.storage_path)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{file_id}.mp4"

    if "application/octet-stream" in content_type:
        # Raw binary upload (iOS streaming mode)
        filename = request.headers.get("x-filename", "video.mp4")
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Desteklenmeyen format: {ext}. Sadece MP4/MOV/M4V.")

        size = 0
        max_size = settings.max_upload_size_mb * 1024 * 1024
        async with aiofiles.open(tmp_path, "wb") as f:
            async for chunk in request.stream():
                size += len(chunk)
                if size > max_size:
                    await aiofiles.os.remove(tmp_path)
                    raise HTTPException(
                        413, f"Dosya çok büyük (maks {settings.max_upload_size_mb}MB)"
                    )
                await f.write(chunk)

    elif file is not None:
        # Multipart form-data upload
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Desteklenmeyen format: {ext}. Sadece MP4/MOV/M4V.")

        size = 0
        max_size = settings.max_upload_size_mb * 1024 * 1024
        async with aiofiles.open(tmp_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                size += len(chunk)
                if size > max_size:
                    await aiofiles.os.remove(tmp_path)
                    raise HTTPException(
                        413, f"Dosya çok büyük (maks {settings.max_upload_size_mb}MB)"
                    )
                await f.write(chunk)

    else:
        raise HTTPException(400, "Dosya bulunamadı. Multipart veya binary upload gönderin.")

    # If using R2, upload the local file to cloud storage
    key = f"{file_id}.mp4"
    if settings.r2_endpoint:
        await storage.save_from_path(key, str(tmp_path))

    # Auto-generate thumbnail (non-blocking, best-effort)
    thumbnail_url = None
    try:
        await generate_thumbnail(str(tmp_path))
        thumbnail_url = f"/api/v1/thumbnails/{file_id}"
    except Exception as e:
        log.warning("thumbnail_generation_failed", file_id=file_id, error=str(e))

    log.info("upload_complete", file_id=file_id, size_mb=round(size / 1024 / 1024, 1))
    return {
        "file_id": file_id,
        "size_mb": round(size / 1024 / 1024, 1),
        "thumbnail_url": thumbnail_url,
    }
