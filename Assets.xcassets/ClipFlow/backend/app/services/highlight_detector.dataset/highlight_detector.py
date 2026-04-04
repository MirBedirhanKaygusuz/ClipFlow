"""Highlight detection — find the most interesting moments in a video.

Uses motion analysis (frame differencing) and audio energy to score
each segment of a video, then returns the top highlights.
"""

import asyncio
import json
import re
import structlog
import numpy as np

from app.services.ffmpeg_runner import run_ffmpeg, run_ffprobe
from app.services.beat_detector import _extract_audio

log = structlog.get_logger()


async def detect_highlights(
    video_path: str,
    max_highlights: int = 10,
    min_duration: float = 1.0,
    max_duration: float = 5.0,
) -> list[dict]:
    """Detect highlight moments in a video based on motion and audio energy.

    Args:
        video_path: Path to the video file.
        max_highlights: Maximum number of highlights to return.
        min_duration: Minimum highlight duration in seconds.
        max_duration: Maximum highlight duration in seconds.

    Returns:
        List of highlight dicts sorted by score (best first), each with:
        - start: Start time in seconds
        - end: End time in seconds
        - score: Combined motion + energy score (0-1)
        - motion_score: Motion intensity (0-1)
        - energy_score: Audio energy (0-1)
    """
    # Run motion and audio analysis concurrently
    motion_task = asyncio.create_task(_analyze_motion(video_path))
    energy_task = asyncio.create_task(_analyze_energy(video_path))
    info_task = asyncio.create_task(_get_duration(video_path))

    motion_scores = await motion_task
    energy_scores = await energy_task
    duration = await info_task

    if not motion_scores and not energy_scores:
        log.warning("highlight_detection_empty", video_path=video_path)
        return []

    # Combine scores into time-aligned segments
    highlights = _combine_and_rank(
        motion_scores=motion_scores,
        energy_scores=energy_scores,
        duration=duration,
        max_highlights=max_highlights,
        min_duration=min_duration,
        max_duration=max_duration,
    )

    log.info("highlights_detected", count=len(highlights))
    return highlights


async def _get_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", video_path,
    ]
    stdout = await run_ffprobe(cmd)
    return float(json.loads(stdout).get("format", {}).get("duration", 0))


async def _analyze_motion(video_path: str) -> list[dict]:
    """Analyze motion intensity using FFmpeg's scene change detection.

    Returns a list of {timestamp, score} dicts where score represents
    the amount of visual change at each frame.
    """
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", "select='gte(scene,0)',metadata=print:file=-",
        "-an", "-f", "null", "-",
    ]

    try:
        _, stderr = await run_ffmpeg(cmd, retries=0, timeout=180)
    except Exception as e:
        log.warning("motion_analysis_failed", error=str(e))
        return []

    scores = []
    current_time = None

    for line in stderr.split("\n"):
        time_match = re.search(r"pts_time:([\d.]+)", line)
        if time_match:
            current_time = float(time_match.group(1))

        score_match = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if score_match and current_time is not None:
            scores.append({
                "timestamp": round(current_time, 3),
                "score": float(score_match.group(1)),
            })

    return scores


async def _analyze_energy(video_path: str) -> list[dict]:
    """Analyze audio energy at regular intervals using librosa.

    Returns a list of {timestamp, score} dicts where score represents
    normalized audio loudness.
    """
    wav_path = await _extract_audio(video_path)
    import os

    try:
        result = await asyncio.to_thread(_librosa_energy, wav_path)
        return result
    except Exception as e:
        log.warning("energy_analysis_failed", error=str(e))
        return []
    finally:
        os.unlink(wav_path)


def _librosa_energy(wav_path: str) -> list[dict]:
    """Compute time-stamped energy scores from audio (blocking)."""
    import librosa

    y, sr = librosa.load(wav_path, sr=22050, mono=True)
    hop_length = 512

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # Normalize to 0-1
    rms_max = rms.max()
    if rms_max == 0:
        return []

    rms_norm = rms / rms_max

    # Downsample to ~4 values per second for efficiency
    step = max(1, int(sr / hop_length / 4))
    scores = []
    for i in range(0, len(rms_norm), step):
        scores.append({
            "timestamp": round(float(times[i]), 3),
            "score": round(float(rms_norm[i]), 4),
        })

    return scores


def _combine_and_rank(
    motion_scores: list[dict],
    energy_scores: list[dict],
    duration: float,
    max_highlights: int,
    min_duration: float,
    max_duration: float,
) -> list[dict]:
    """Combine motion and energy scores, then extract top highlight segments.

    Uses a sliding window approach to find segments with the highest
    combined score.
    """
    if duration <= 0:
        return []

    # Build a unified timeline at 0.25s resolution
    resolution = 0.25
    num_bins = int(duration / resolution) + 1
    motion_timeline = np.zeros(num_bins)
    energy_timeline = np.zeros(num_bins)

    for s in motion_scores:
        idx = min(int(s["timestamp"] / resolution), num_bins - 1)
        motion_timeline[idx] = max(motion_timeline[idx], s["score"])

    for s in energy_scores:
        idx = min(int(s["timestamp"] / resolution), num_bins - 1)
        energy_timeline[idx] = max(energy_timeline[idx], s["score"])

    # Normalize motion timeline
    m_max = motion_timeline.max()
    if m_max > 0:
        motion_timeline /= m_max

    # Combined score: 60% motion + 40% audio energy
    combined = 0.6 * motion_timeline + 0.4 * energy_timeline

    # Sliding window to find best segments
    window_bins = int(max_duration / resolution)
    min_bins = int(min_duration / resolution)
    candidates = []

    for size in range(min_bins, window_bins + 1):
        for start in range(0, num_bins - size):
            segment_score = float(np.mean(combined[start : start + size]))
            start_time = start * resolution
            end_time = (start + size) * resolution
            candidates.append({
                "start": round(start_time, 2),
                "end": round(end_time, 2),
                "score": round(segment_score, 4),
                "motion_score": round(float(np.mean(motion_timeline[start : start + size])), 4),
                "energy_score": round(float(np.mean(energy_timeline[start : start + size])), 4),
            })

    # Sort by score, deduplicate overlapping segments
    candidates.sort(key=lambda x: x["score"], reverse=True)

    highlights = []
    for c in candidates:
        if len(highlights) >= max_highlights:
            break
        # Check overlap with existing highlights
        overlap = False
        for h in highlights:
            if c["start"] < h["end"] and c["end"] > h["start"]:
                overlap = True
                break
        if not overlap:
            highlights.append(c)

    # Sort by time for output
    highlights.sort(key=lambda x: x["start"])
    return highlights
