"""Audio waveform generation for timeline visualization.

Extracts audio amplitude data from video/audio files and returns
normalized sample arrays suitable for rendering waveform visualizations.
"""

import asyncio
import json
import structlog
from pathlib import Path

from app.services.ffmpeg_runner import run_ffmpeg, run_ffprobe

log = structlog.get_logger()


async def generate_waveform(
    media_path: str,
    samples: int = 200,
) -> dict:
    """Generate waveform data from a video or audio file.

    Extracts audio, computes RMS amplitude at evenly spaced intervals,
    and returns normalized values (0.0-1.0) for visualization.

    Args:
        media_path: Path to the video or audio file.
        samples: Number of waveform samples to generate (default 200).

    Returns:
        Dict with "samples" (list of floats 0-1), "duration", "sample_rate".
    """
    duration = await _get_duration(media_path)
    if duration <= 0:
        return {"samples": [], "duration": 0, "sample_rate": 0}

    # Use FFmpeg to extract audio peaks
    # astats filter can compute RMS per window
    # Alternatively, use volumedetect with segments
    waveform_data = await _extract_peaks(media_path, samples, duration)

    return {
        "samples": waveform_data,
        "duration": round(duration, 2),
        "sample_count": len(waveform_data),
        "samples_per_second": round(len(waveform_data) / duration, 2) if duration > 0 else 0,
    }


async def _extract_peaks(
    media_path: str,
    num_samples: int,
    duration: float,
) -> list[float]:
    """Extract audio peaks using FFmpeg's ebur128 or astats filter.

    Uses FFmpeg to compute audio levels at regular intervals.
    Falls back to librosa if FFmpeg approach fails.
    """
    # Use FFmpeg to get audio samples at specific intervals
    # The approach: extract raw PCM audio, read peaks at regular intervals
    # Using astats with reset interval
    interval = duration / num_samples if num_samples > 0 else 1.0

    cmd = [
        "ffmpeg", "-i", media_path,
        "-af", f"astats=metadata=1:reset={max(int(interval * 44100), 1)},ametadata=print:file=-",
        "-f", "null", "-",
    ]

    try:
        _, stderr = await run_ffmpeg(cmd, retries=0, timeout=60)
    except Exception as e:
        log.warning("waveform_ffmpeg_failed", error=str(e))
        return await _fallback_librosa(media_path, num_samples)

    # Parse RMS levels from astats output
    import re
    rms_values = []
    for line in stderr.split("\n"):
        match = re.search(r"RMS_level=([-\d.]+)", line)
        if match:
            val = float(match.group(1))
            if val > -100:  # Skip silence (very low dB)
                rms_values.append(val)

    if not rms_values:
        return await _fallback_librosa(media_path, num_samples)

    # Downsample to requested number of samples
    if len(rms_values) > num_samples:
        step = len(rms_values) / num_samples
        rms_values = [rms_values[int(i * step)] for i in range(num_samples)]

    # Normalize dB values to 0-1 range
    # Typical range: -60dB (silence) to 0dB (max)
    min_db = -60.0
    max_db = max(rms_values) if rms_values else 0
    db_range = max_db - min_db if max_db > min_db else 1.0

    normalized = []
    for val in rms_values:
        norm = max(0.0, min(1.0, (val - min_db) / db_range))
        normalized.append(round(norm, 4))

    return normalized


async def _fallback_librosa(media_path: str, num_samples: int) -> list[float]:
    """Fallback: use librosa for waveform extraction."""
    try:
        result = await asyncio.to_thread(_librosa_waveform, media_path, num_samples)
        return result
    except Exception as e:
        log.warning("waveform_librosa_failed", error=str(e))
        return []


def _librosa_waveform(media_path: str, num_samples: int) -> list[float]:
    """Compute waveform peaks using librosa (blocking)."""
    import librosa
    import numpy as np

    y, sr = librosa.load(media_path, sr=22050, mono=True)
    if len(y) == 0:
        return []

    # Compute RMS in windows
    hop_length = max(1, len(y) // num_samples)
    rms = librosa.feature.rms(y=y, frame_length=hop_length * 2, hop_length=hop_length)[0]

    # Normalize to 0-1
    rms_max = rms.max()
    if rms_max == 0:
        return [0.0] * min(len(rms), num_samples)

    rms_norm = rms / rms_max

    # Downsample if needed
    if len(rms_norm) > num_samples:
        step = len(rms_norm) / num_samples
        rms_norm = [float(rms_norm[int(i * step)]) for i in range(num_samples)]
    else:
        rms_norm = [float(v) for v in rms_norm]

    return [round(v, 4) for v in rms_norm[:num_samples]]


async def _get_duration(media_path: str) -> float:
    """Get media duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", media_path,
    ]
    try:
        stdout = await run_ffprobe(cmd)
        return float(json.loads(stdout).get("format", {}).get("duration", 0))
    except Exception:
        return 0.0
