"""Video thumbnail generation using FFmpeg.

Generates representative thumbnails at key moments in the video.
Uses scene detection to pick the most visually interesting frame.
"""

import json
import re
import structlog
from pathlib import Path

from app.services.ffmpeg_runner import run_ffmpeg, run_ffprobe
from app.config import settings

log = structlog.get_logger()

# Thumbnail dimensions
THUMB_WIDTH = 480
THUMB_HEIGHT = 854  # 9:16 ratio


async def generate_thumbnail(
    video_path: str,
    output_path: str | None = None,
    timestamp: float | None = None,
    width: int = THUMB_WIDTH,
    height: int = THUMB_HEIGHT,
) -> str:
    """Generate a single thumbnail from a video.

    If no timestamp given, automatically picks the most visually
    interesting frame using scene detection.

    Args:
        video_path: Path to the video file.
        output_path: Where to save the thumbnail. If None, auto-generates.
        timestamp: Specific timestamp to capture. None = auto-detect best frame.
        width: Thumbnail width.
        height: Thumbnail height.

    Returns:
        Path to the generated thumbnail file.
    """
    if output_path is None:
        stem = Path(video_path).stem
        output_path = str(Path(settings.storage_path) / "thumbnails" / f"{stem}.jpg")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if timestamp is None:
        timestamp = await _find_best_frame(video_path)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-q:v", "2",  # JPEG quality (1-31, lower = better)
        output_path,
    ]
    await run_ffmpeg(cmd, retries=1, timeout=30)

    log.info("thumbnail_generated", video_path=video_path, output=output_path, timestamp=timestamp)
    return output_path


async def generate_thumbnail_strip(
    video_path: str,
    output_dir: str | None = None,
    count: int = 5,
    width: int = 160,
    height: int = 90,
) -> list[str]:
    """Generate multiple thumbnails evenly spaced through the video.

    Useful for timeline scrubbing UI.

    Args:
        video_path: Path to the video file.
        output_dir: Directory to save thumbnails. None = auto.
        count: Number of thumbnails to generate.
        width: Thumbnail width.
        height: Thumbnail height.

    Returns:
        List of paths to generated thumbnail files.
    """
    duration = await _get_duration(video_path)
    if duration <= 0:
        return []

    if output_dir is None:
        stem = Path(video_path).stem
        output_dir = str(Path(settings.storage_path) / "thumbnails" / stem)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    paths = []
    interval = duration / (count + 1)

    for i in range(count):
        t = interval * (i + 1)
        out_path = str(Path(output_dir) / f"frame_{i:03d}.jpg")

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(t, 2)),
            "-i", video_path,
            "-vframes", "1",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            "-q:v", "3",
            out_path,
        ]
        await run_ffmpeg(cmd, retries=0, timeout=15)
        paths.append(out_path)

    log.info("thumbnail_strip_generated", count=len(paths))
    return paths


async def _find_best_frame(video_path: str) -> float:
    """Find the most visually interesting frame timestamp.

    Uses FFmpeg scene detection to find the first significant scene change,
    which typically contains a representative frame.

    Falls back to 25% of duration if no scene change found.
    """
    duration = await _get_duration(video_path)
    if duration <= 0:
        return 0.0

    # Try to find the first interesting scene change
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", "select='gt(scene,0.3)',metadata=print:file=-",
        "-an", "-f", "null", "-",
    ]

    try:
        _, stderr = await run_ffmpeg(cmd, retries=0, timeout=30)

        for line in stderr.split("\n"):
            time_match = re.search(r"pts_time:([\d.]+)", line)
            if time_match:
                t = float(time_match.group(1))
                if t > 0.5:  # Skip very early frames (often black)
                    return min(t, duration)
    except Exception:
        pass

    # Fallback: 25% of duration
    return duration * 0.25


async def _get_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", video_path,
    ]
    try:
        stdout = await run_ffprobe(cmd)
        return float(json.loads(stdout).get("format", {}).get("duration", 0))
    except Exception:
        return 0.0
