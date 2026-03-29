"""Silence detection and removal using FFmpeg."""

import subprocess
import json
import re
from app.config import settings


def get_duration(path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def detect_silence(input_path: str) -> list[dict]:
    """Detect silent segments in video using FFmpeg silencedetect."""
    cmd = [
        "ffmpeg", "-i", input_path,
        "-af", f"silencedetect=noise={settings.silence_threshold_db}dB:d={settings.min_silence_duration}",
        "-f", "null", "-"
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


def cut_silences(input_path: str, output_path: str, silences: list[dict]) -> dict:
    """Remove silent segments and concatenate speaking parts."""
    duration = get_duration(input_path)

    # Calculate speaking segments
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

    # Build FFmpeg filter_complex
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

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", settings.ffmpeg_preset,
        "-c:a", "aac",
        output_path
    ]
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
