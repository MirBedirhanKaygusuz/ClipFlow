"""Video validation and metadata extraction.

Validates uploaded videos for codec, duration, resolution, and integrity.
Provides auto-split suggestions for videos exceeding platform limits.
"""

import json
import structlog
from dataclasses import dataclass

from app.services.ffmpeg_runner import run_ffprobe

log = structlog.get_logger()

# Platform limits for Reels/Story
REELS_MAX_DURATION = 90.0  # seconds
STORY_MAX_DURATION = 60.0
MAX_SUPPORTED_DURATION = 3600.0  # 1 hour absolute max

SUPPORTED_VIDEO_CODECS = {"h264", "hevc", "h265", "vp9", "av1", "mpeg4"}
SUPPORTED_AUDIO_CODECS = {"aac", "mp3", "opus", "vorbis", "pcm_s16le", "flac"}


@dataclass
class VideoInfo:
    """Validated video metadata."""

    duration: float
    width: int
    height: int
    video_codec: str
    audio_codec: str | None
    fps: float
    bitrate: int  # kbps
    file_size_mb: float
    has_audio: bool
    rotation: int  # 0, 90, 180, 270


@dataclass
class ValidationResult:
    """Result of video validation."""

    valid: bool
    info: VideoInfo | None
    errors: list[str]
    warnings: list[str]


async def validate_video(video_path: str) -> ValidationResult:
    """Validate a video file and extract metadata.

    Checks:
    - File is a valid video (has video stream)
    - Video codec is supported
    - Duration is within limits
    - Resolution is reasonable (at least 240p)

    Args:
        video_path: Path to the video file.

    Returns:
        ValidationResult with metadata and any errors/warnings.
    """
    errors = []
    warnings = []

    try:
        info = await _extract_info(video_path)
    except Exception as e:
        return ValidationResult(
            valid=False,
            info=None,
            errors=[f"Video okunamadı: {str(e)[:100]}"],
            warnings=[],
        )

    # Check video codec
    if info.video_codec.lower() not in SUPPORTED_VIDEO_CODECS:
        warnings.append(
            f"Video codec '{info.video_codec}' desteklenmeyebilir. "
            f"Desteklenen: {', '.join(sorted(SUPPORTED_VIDEO_CODECS))}"
        )

    # Check duration
    if info.duration <= 0:
        errors.append("Video süresi tespit edilemedi.")
    elif info.duration > MAX_SUPPORTED_DURATION:
        errors.append(
            f"Video çok uzun ({info.duration:.0f}s). "
            f"Maksimum {MAX_SUPPORTED_DURATION:.0f}s destekleniyor."
        )

    # Check resolution
    if info.width < 240 or info.height < 240:
        warnings.append(
            f"Video çözünürlüğü çok düşük ({info.width}x{info.height}). "
            "En az 240p önerilir."
        )

    # Check audio
    if not info.has_audio:
        warnings.append("Video'da ses kanalı bulunamadı.")

    # Reels-specific warnings
    if info.duration > REELS_MAX_DURATION:
        warnings.append(
            f"Video süresi ({info.duration:.0f}s) Instagram Reels limiti olan "
            f"{REELS_MAX_DURATION:.0f}s'yi aşıyor. İşlemden sonra kısaltılabilir."
        )

    log.info(
        "video_validated",
        path=video_path,
        valid=len(errors) == 0,
        duration=info.duration,
        resolution=f"{info.width}x{info.height}",
        codec=info.video_codec,
    )

    return ValidationResult(
        valid=len(errors) == 0,
        info=info,
        errors=errors,
        warnings=warnings,
    )


async def suggest_splits(
    video_path: str,
    max_duration: float = REELS_MAX_DURATION,
) -> list[dict]:
    """Suggest optimal split points for a video that exceeds max_duration.

    Uses scene detection to find natural cut points near the split boundaries,
    so splits happen at scene changes rather than mid-scene.

    Args:
        video_path: Path to the video file.
        max_duration: Maximum duration per segment.

    Returns:
        List of {"start": float, "end": float, "part": int} dicts.
    """
    result = await validate_video(video_path)
    if not result.info or result.info.duration <= max_duration:
        return []

    duration = result.info.duration
    num_parts = int(duration / max_duration) + 1

    # Get scene change timestamps for smart splitting
    scene_times = await _detect_scene_changes(video_path)

    segments = []
    current_start = 0.0

    for part in range(num_parts):
        ideal_end = min(current_start + max_duration, duration)

        if part < num_parts - 1 and scene_times:
            # Find the nearest scene change to the ideal split point
            best_cut = ideal_end
            best_dist = float("inf")
            for st in scene_times:
                if current_start < st < ideal_end + 5.0:  # Allow 5s flexibility
                    dist = abs(st - ideal_end)
                    if dist < best_dist:
                        best_dist = dist
                        best_cut = st

            ideal_end = best_cut

        segments.append({
            "start": round(current_start, 2),
            "end": round(min(ideal_end, duration), 2),
            "part": part + 1,
            "duration": round(min(ideal_end, duration) - current_start, 2),
        })

        current_start = ideal_end
        if current_start >= duration:
            break

    log.info("split_suggested", parts=len(segments), total_duration=duration)
    return segments


async def _extract_info(video_path: str) -> VideoInfo:
    """Extract video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path,
    ]
    stdout = await run_ffprobe(cmd)
    data = json.loads(stdout)

    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))
    file_size_mb = round(int(fmt.get("size", 0)) / 1024 / 1024, 1)
    bitrate = int(fmt.get("bit_rate", 0)) // 1000

    video_codec = ""
    audio_codec = None
    width = 0
    height = 0
    fps = 0.0
    rotation = 0
    has_audio = False

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and not video_codec:
            video_codec = stream.get("codec_name", "unknown")
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))

            # Parse FPS from r_frame_rate (e.g., "30/1" or "30000/1001")
            r_fps = stream.get("r_frame_rate", "0/1")
            parts = r_fps.split("/")
            if len(parts) == 2 and int(parts[1]) > 0:
                fps = round(int(parts[0]) / int(parts[1]), 2)

            # Check rotation
            tags = stream.get("tags", {})
            rotation = int(tags.get("rotate", 0))
            # Also check side_data for rotation
            for sd in stream.get("side_data_list", []):
                if "rotation" in sd:
                    rotation = abs(int(sd["rotation"]))

        elif stream.get("codec_type") == "audio":
            audio_codec = stream.get("codec_name", "unknown")
            has_audio = True

    return VideoInfo(
        duration=duration,
        width=width,
        height=height,
        video_codec=video_codec,
        audio_codec=audio_codec,
        fps=fps,
        bitrate=bitrate,
        file_size_mb=file_size_mb,
        has_audio=has_audio,
        rotation=rotation,
    )


async def _detect_scene_changes(video_path: str) -> list[float]:
    """Detect scene change timestamps for smart splitting."""
    from app.services.ffmpeg_runner import run_ffmpeg
    import re

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", "select='gt(scene,0.3)',metadata=print:file=-",
        "-an", "-f", "null", "-",
    ]

    try:
        _, stderr = await run_ffmpeg(cmd, retries=0, timeout=120)
    except Exception:
        return []

    times = []
    for line in stderr.split("\n"):
        match = re.search(r"pts_time:([\d.]+)", line)
        if match:
            times.append(float(match.group(1)))

    return times
