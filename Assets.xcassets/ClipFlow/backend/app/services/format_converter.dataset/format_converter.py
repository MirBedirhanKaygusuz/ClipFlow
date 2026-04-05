"""Video format conversion — 9:16 vertical with optional smart zoom/crop (async)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import settings
from app.services.ffmpeg_runner import run_ffmpeg, run_ffprobe

if TYPE_CHECKING:
    from app.services.zoom_analyzer import ZoomKeyframe

import json


async def convert_to_vertical(
    input_path: str,
    output_path: str,
    zoom_keyframes: list[ZoomKeyframe] | None = None,
) -> None:
    """Convert video to 9:16 vertical format (1080x1920).

    If zoom_keyframes are provided, uses smart zoom/crop to focus on
    the most interesting regions. Otherwise falls back to center crop.

    Args:
        input_path: Source video file path.
        output_path: Destination file path for converted video.
        zoom_keyframes: Optional zoom keyframes from zoom_analyzer.
    """
    if zoom_keyframes:
        await _convert_with_zoom(input_path, output_path, zoom_keyframes)
    else:
        await _convert_center_crop(input_path, output_path)


async def _convert_center_crop(input_path: str, output_path: str) -> None:
    """Convert to 9:16 with centered letterbox/pillarbox (original behavior)."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
        ),
        "-c:v", "libx264", "-preset", settings.ffmpeg_preset,
        "-c:a", "aac",
        output_path,
    ]
    await run_ffmpeg(cmd, retries=1, timeout=300)


async def _convert_with_zoom(
    input_path: str,
    output_path: str,
    keyframes: list[ZoomKeyframe],
) -> None:
    """Convert to 9:16 with AI-driven zoom/crop based on keyframes.

    Uses FFmpeg zoompan filter to smoothly animate between zoom positions,
    keeping the most interesting content in frame.
    """
    from app.services.zoom_analyzer import build_zoompan_filter

    # Get source video dimensions
    width, height = await _get_dimensions(input_path)
    if width <= 0 or height <= 0:
        # Fallback to center crop if we can't get dimensions
        await _convert_center_crop(input_path, output_path)
        return

    # Build the zoompan filter expression
    vf = build_zoompan_filter(
        keyframes=keyframes,
        input_width=width,
        input_height=height,
        output_width=1080,
        output_height=1920,
        fps=30,
    )

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", settings.ffmpeg_preset,
        "-c:a", "aac",
        "-r", "30",
        output_path,
    ]
    await run_ffmpeg(cmd, retries=1, timeout=600)


async def _get_dimensions(video_path: str) -> tuple[int, int]:
    """Get video width and height."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", video_path,
    ]
    stdout = await run_ffprobe(cmd)
    data = json.loads(stdout)

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return int(stream.get("width", 0)), int(stream.get("height", 0))
    return 0, 0
