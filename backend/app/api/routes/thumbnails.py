"""Thumbnail generation endpoint."""

import asyncio
import subprocess
from pathlib import Path

import structlog
from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import settings
from app.exceptions import ClipFlowError, FFmpegError

router = APIRouter()
log = structlog.get_logger()

THUMBNAIL_DIR_NAME = "thumbnails"
THUMBNAIL_QUALITY = 3   # FFmpeg -q:v scale: 2 (best) – 31 (worst); 3 is near-lossless


class FileNotFoundError(ClipFlowError):
    """Raised when the source video file cannot be located."""

    def __init__(self, file_id: str) -> None:
        """Initialise with the missing file_id.

        Args:
            file_id: The file_id that could not be resolved to a video.
        """
        super().__init__(f"Video file not found: {file_id}", 404)


def _find_video_path(file_id: str) -> Path:
    """Locate a previously uploaded video by its file_id.

    Searches <storage_path> for any file whose stem matches *file_id*.

    Args:
        file_id: UUID returned by the upload endpoint.

    Returns:
        Absolute Path to the video file.

    Raises:
        FileNotFoundError: If no matching file is found.
    """
    storage = Path(settings.storage_path)
    for ext in (".mp4", ".mov", ".m4v"):
        candidate = storage / f"{file_id}{ext}"
        if candidate.exists():
            return candidate
    # Fallback: glob for any extension
    matches = list(storage.glob(f"{file_id}.*"))
    if matches:
        return matches[0]
    raise FileNotFoundError(file_id)


def _thumbnail_dir() -> Path:
    """Return (and create) the thumbnail cache directory.

    Returns:
        Absolute Path to the thumbnail storage directory.
    """
    thumb_dir = Path(settings.storage_path) / THUMBNAIL_DIR_NAME
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return thumb_dir


async def _generate_thumbnail(video_path: Path, thumb_path: Path) -> None:
    """Extract a JPEG frame at 25 % of the video duration via FFmpeg.

    Args:
        video_path: Absolute path to the source video.
        thumb_path: Destination path for the JPEG thumbnail.

    Raises:
        FFmpegError: If FFmpeg returns a non-zero exit code.
    """
    # Step 1: Probe duration
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        probe = await asyncio.to_thread(
            subprocess.run,
            probe_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError("ffprobe timed out while reading duration") from exc

    if probe.returncode != 0:
        raise FFmpegError(probe.stderr)

    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        duration = 0.0

    seek_time = max(0.0, duration * 0.25)

    # Step 2: Extract frame
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(seek_time),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", str(THUMBNAIL_QUALITY),
        "-f", "image2",
        str(thumb_path),
    ]
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError("ffmpeg timed out during thumbnail extraction") from exc

    if result.returncode != 0:
        raise FFmpegError(result.stderr)

    log.info(
        "thumbnail_generated",
        video=str(video_path),
        thumb=str(thumb_path),
        seek_time=round(seek_time, 2),
    )


@router.get("/thumbnails/{file_id}")
async def get_thumbnail(file_id: str) -> FileResponse:
    """Return a JPEG thumbnail for a previously uploaded video.

    If the thumbnail has already been generated it is served directly
    from the cache.  Otherwise it is generated on demand by extracting
    a frame at 25 % of the video duration via FFmpeg.

    Args:
        file_id: UUID returned by the ``POST /upload`` endpoint.

    Returns:
        A JPEG image response (``image/jpeg``).

    Raises:
        FileNotFoundError: If no video with the given file_id exists.
        FFmpegError: If FFmpeg fails to extract the frame.
    """
    thumb_path = _thumbnail_dir() / f"{file_id}.jpg"

    if not thumb_path.exists():
        video_path = _find_video_path(file_id)
        await _generate_thumbnail(video_path, thumb_path)

    return FileResponse(
        path=str(thumb_path),
        media_type="image/jpeg",
        filename=f"{file_id}.jpg",
    )
