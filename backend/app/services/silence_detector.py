"""Silence detection and removal using FFmpeg."""

import subprocess
import json
import re

from app.config import settings
from app.models.job import QualityMode


def get_duration(path: str) -> float:
    """Get video duration in seconds.

    Args:
        path: Video file path.

    Returns:
        Duration in seconds.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def detect_silence(input_path: str) -> list[dict]:
    """Detect silent segments in video using FFmpeg silencedetect.

    Args:
        input_path: Video file path.

    Returns:
        List of dicts with "start" and "end" keys (seconds).
    """
    cmd = [
        "ffmpeg", "-i", input_path,
        "-af", f"silencedetect=noise={settings.silence_threshold_db}dB:d={settings.min_silence_duration}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    silences = []
    for line in result.stderr.split("\n"):
        if "silence_start" in line:
            match = re.search(r"silence_start: ([\d.]+)", line)
            if match:
                silences.append({"start": float(match.group(1))})
        elif "silence_end" in line and silences:
            match = re.search(r"silence_end: ([\d.]+)", line)
            if match:
                silences[-1]["end"] = float(match.group(1))

    return silences


def _build_filter_complex(speaking: list[tuple[float, float]]) -> str:
    """Build FFmpeg filter_complex string for trim + concat.

    Args:
        speaking: List of (start, end) tuples for speaking segments.

    Returns:
        FFmpeg filter_complex string.
    """
    filter_parts = []
    for i, (start, end) in enumerate(speaking):
        filter_parts.append(
            f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}];"
            f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]"
        )

    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(speaking)))
    filter_parts.append(
        f"{concat_inputs}concat=n={len(speaking)}:v=1:a=1[outv][outa]"
    )
    return ";".join(filter_parts)


def _get_speaking_segments(silences: list[dict], duration: float) -> list[tuple[float, float]]:
    """Calculate speaking segments from silence list.

    Args:
        silences: List of silence dicts with "start" and "end".
        duration: Total video duration in seconds.

    Returns:
        List of (start, end) tuples for speaking segments.
    """
    speaking = []
    prev_end = 0.0
    for s in silences:
        if s["start"] - prev_end > 0.05:
            speaking.append((prev_end, s["start"]))
        prev_end = s.get("end", s["start"] + 0.5)

    if duration - prev_end > 0.05:
        speaking.append((prev_end, duration))

    if not speaking:
        speaking = [(0, duration)]

    return speaking


def cut_silences(
    input_path: str,
    output_path: str,
    silences: list[dict],
    quality: QualityMode = QualityMode.REELS,
) -> dict:
    """Remove silent segments and concatenate speaking parts.

    Encoding varies by quality mode:
    - REELS: fast intermediate (will be re-encoded by encode_reels)
    - HIGH_QUALITY: final output directly (CRF 17, 320k audio, no second pass)

    Args:
        input_path: Source video file path.
        output_path: Destination file path.
        silences: List of silence dicts from detect_silence().
        quality: QualityMode controlling encoding settings.

    Returns:
        Dict with processing stats.
    """
    duration = get_duration(input_path)
    speaking = _get_speaking_segments(silences, duration)
    filter_complex = _build_filter_complex(speaking)

    # Base command
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
    ]

    if quality == QualityMode.HIGH_QUALITY:
        # Final output — visually lossless, preserve original resolution
        cmd += [
            "-c:v", "libx264", "-crf", "17",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
            "-movflags", "+faststart",
        ]
    else:
        # Intermediate — will be re-encoded by encode_reels
        cmd += [
            "-c:v", "libx264", "-crf", "20",
            "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
        ]

    cmd.append(output_path)
    subprocess.run(cmd, check=True, capture_output=True)

    # Calculate stats
    new_duration = get_duration(output_path)
    silence_removed = duration - new_duration
    return {
        "original_duration": round(duration, 1),
        "new_duration": round(new_duration, 1),
        "silence_removed_seconds": round(silence_removed, 1),
        "silence_removed_pct": round(silence_removed / duration * 100, 1) if duration > 0 else 0,
        "segments": len(speaking),
    }
