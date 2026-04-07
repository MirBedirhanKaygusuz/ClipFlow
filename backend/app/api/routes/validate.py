"""Video validation and metadata extraction endpoint."""

import json
import subprocess
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter()
log = structlog.get_logger()


class VideoMetadata(BaseModel):
    """Video file metadata from ffprobe."""

    duration: float
    width: int
    height: int
    video_codec: str
    audio_codec: str | None = None
    fps: float
    bitrate_kbps: int
    file_size_mb: float
    has_audio: bool
    rotation: int = 0


class ValidationResult(BaseModel):
    """Video validation result."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    info: VideoMetadata | None = None


def _probe_video(file_path: str) -> dict:
    """Run ffprobe and return parsed JSON output.

    Args:
        file_path: Path to the video file.

    Returns:
        Parsed ffprobe JSON output.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


@router.get("/validate/{file_id}", response_model=ValidationResult)
async def validate_video(file_id: str) -> ValidationResult:
    """Validate an uploaded video and return metadata.

    Args:
        file_id: The uploaded file identifier.

    Returns:
        ValidationResult with metadata, errors, and warnings.
    """
    storage_dir = Path(settings.storage_path)
    file_path = next(
        (p for ext in (".mp4", ".mov", ".m4v")
         if (p := storage_dir / f"{file_id}{ext}").exists()),
        None,
    )

    if not file_path:
        raise HTTPException(404, f"Dosya bulunamadı: {file_id}")

    try:
        probe = _probe_video(str(file_path))
    except subprocess.CalledProcessError as e:
        raise HTTPException(422, f"Video okunamadı: {e.stderr[:200]}")

    errors: list[str] = []
    warnings: list[str] = []

    video_stream = next(
        (s for s in probe.get("streams", []) if s["codec_type"] == "video"), None
    )
    audio_stream = next(
        (s for s in probe.get("streams", []) if s["codec_type"] == "audio"), None
    )
    fmt = probe.get("format", {})

    if not video_stream:
        return ValidationResult(valid=False, errors=["Video akışı bulunamadı"], warnings=[])

    duration = float(fmt.get("duration", 0))
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    video_codec = video_stream.get("codec_name", "unknown")
    audio_codec = audio_stream.get("codec_name") if audio_stream else None
    bitrate = int(fmt.get("bit_rate", 0)) // 1000
    file_size = float(fmt.get("size", 0)) / (1024 * 1024)
    has_audio = audio_stream is not None

    fps_str = video_stream.get("r_frame_rate", "30/1")
    try:
        num, den = fps_str.split("/")
        fps = round(float(num) / float(den), 2)
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    rotation = 0
    for sd in video_stream.get("side_data_list", []):
        if "rotation" in sd:
            rotation = abs(int(sd["rotation"]))

    if duration > 3600:
        errors.append("Video 1 saatten uzun")
    elif duration > 600:
        warnings.append("Video 10 dakikadan uzun, işleme süresi artabilir")

    if width < 480 or height < 480:
        warnings.append(f"Düşük çözünürlük: {width}x{height}")

    if not has_audio:
        warnings.append("Ses akışı bulunamadı")

    metadata = VideoMetadata(
        duration=round(duration, 2), width=width, height=height,
        video_codec=video_codec, audio_codec=audio_codec, fps=fps,
        bitrate_kbps=bitrate, file_size_mb=round(file_size, 2),
        has_audio=has_audio, rotation=rotation,
    )

    valid = len(errors) == 0
    log.info("video_validated", file_id=file_id, valid=valid, duration=duration)
    return ValidationResult(valid=valid, errors=errors, warnings=warnings, info=metadata)
