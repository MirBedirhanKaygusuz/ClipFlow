"""Music library endpoints — upload, list, analyze, delete music tracks."""

import json
import structlog
from fastapi import APIRouter, HTTPException, Request, UploadFile
from pathlib import Path
from uuid import uuid4
import aiofiles

from app.config import settings
from app.services.beat_detector import detect_beats_from_music

router = APIRouter()
log = structlog.get_logger()

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}


def _music_meta_dir() -> Path:
    """Get the music metadata storage directory."""
    path = Path(settings.storage_path) / "music"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post("/music/upload")
async def upload_music(request: Request, file: UploadFile | None = None):
    """Upload a music track for use in musical edits.

    Supports both multipart and raw binary upload.
    """
    content_type = request.headers.get("content-type", "")
    music_id = str(uuid4())
    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)

    if "application/octet-stream" in content_type:
        filename = request.headers.get("x-filename", "track.mp3")
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(400, f"Desteklenmeyen format: {ext}")

        file_path = storage_dir / f"{music_id}.mp4"  # Store as mp4 for consistency
        size = 0
        async with aiofiles.open(file_path, "wb") as f:
            async for chunk in request.stream():
                size += len(chunk)
                if size > 50 * 1024 * 1024:  # 50MB max for music
                    await aiofiles.os.remove(file_path)
                    raise HTTPException(413, "Müzik dosyası çok büyük (maks 50MB)")
                await f.write(chunk)

    elif file is not None:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(400, f"Desteklenmeyen format: {ext}")

        file_path = storage_dir / f"{music_id}.mp4"
        size = 0
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 50 * 1024 * 1024:
                    await aiofiles.os.remove(file_path)
                    raise HTTPException(413, "Müzik dosyası çok büyük (maks 50MB)")
                await f.write(chunk)
    else:
        raise HTTPException(400, "Dosya bulunamadı.")

    # Save metadata
    filename_display = (
        request.headers.get("x-filename", "track.mp3")
        if "application/octet-stream" in content_type
        else (file.filename or "track.mp3")
    )
    meta = {
        "id": music_id,
        "filename": filename_display,
        "size_mb": round(size / 1024 / 1024, 1),
    }
    meta_path = _music_meta_dir() / f"{music_id}.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    log.info("music_uploaded", id=music_id, size_mb=meta["size_mb"])
    return meta


@router.post("/music/{music_id}/analyze")
async def analyze_music(music_id: str):
    """Analyze beats and tempo of an uploaded music track.

    Returns beat positions, tempo, and musical structure.
    """
    file_path = Path(settings.storage_path) / f"{music_id}.mp4"
    if not file_path.exists():
        raise HTTPException(404, f"Müzik dosyası bulunamadı: {music_id}")

    beats = await detect_beats_from_music(str(file_path))

    # Update metadata with analysis
    meta_path = _music_meta_dir() / f"{music_id}.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta["tempo"] = beats.get("tempo")
        meta["beat_count"] = beats.get("beat_count")
        meta["duration"] = beats.get("duration")
        meta_path.write_text(json.dumps(meta, indent=2))

    return beats


@router.get("/music")
async def list_music():
    """List all uploaded music tracks with metadata."""
    tracks = []
    for meta_file in _music_meta_dir().glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            tracks.append(meta)
        except Exception as e:
            log.warning("music_meta_error", file=str(meta_file), error=str(e))

    return tracks


@router.delete("/music/{music_id}")
async def delete_music(music_id: str):
    """Delete an uploaded music track."""
    file_path = Path(settings.storage_path) / f"{music_id}.mp4"
    meta_path = _music_meta_dir() / f"{music_id}.json"

    if not file_path.exists() and not meta_path.exists():
        raise HTTPException(404, f"Müzik dosyası bulunamadı: {music_id}")

    file_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)

    log.info("music_deleted", id=music_id)
    return {"status": "deleted", "id": music_id}
