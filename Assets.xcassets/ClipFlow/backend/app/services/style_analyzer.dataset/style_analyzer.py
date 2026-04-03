"""Video style analysis — scene detection + audio analysis."""

import asyncio
import json
import tempfile
import structlog
import numpy as np

from app.services.ffmpeg_runner import run_ffmpeg, run_ffprobe

log = structlog.get_logger()


async def analyze_style(video_path: str) -> dict:
    """Analyze a video's editing style characteristics.

    Uses PySceneDetect for visual analysis and librosa for audio analysis.

    Args:
        video_path: Path to the video file.

    Returns:
        Dict with style profile containing scene, audio, and timing metrics.
    """
    # Run scene analysis and audio analysis concurrently
    scene_task = asyncio.create_task(_analyze_scenes(video_path))
    audio_task = asyncio.create_task(_analyze_audio(video_path))
    duration_task = asyncio.create_task(_get_video_info(video_path))

    scenes = await scene_task
    audio = await audio_task
    info = await duration_task

    duration = info.get("duration", 0)
    scene_count = len(scenes)

    return {
        "duration": round(duration, 2),
        "scene_count": scene_count,
        "avg_scene_duration": (
            round(duration / scene_count, 2) if scene_count > 0 else duration
        ),
        "cut_frequency": (
            round(scene_count / duration * 60, 2) if duration > 0 else 0
        ),  # cuts per minute
        "scenes": scenes,
        "audio": audio,
        "resolution": info.get("resolution"),
        "fps": info.get("fps"),
    }


async def _get_video_info(video_path: str) -> dict:
    """Extract video metadata using ffprobe.

    Returns:
        Dict with duration, resolution, fps.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path,
    ]
    stdout = await run_ffprobe(cmd)
    data = json.loads(stdout)

    duration = float(data.get("format", {}).get("duration", 0))
    resolution = None
    fps = None

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            resolution = f"{stream.get('width', '?')}x{stream.get('height', '?')}"
            r_frame_rate = stream.get("r_frame_rate", "0/1")
            parts = r_frame_rate.split("/")
            if len(parts) == 2 and int(parts[1]) > 0:
                fps = round(int(parts[0]) / int(parts[1]), 2)
            break

    return {"duration": duration, "resolution": resolution, "fps": fps}


async def _analyze_scenes(video_path: str) -> list[dict]:
    """Detect scene changes using FFmpeg scene filter.

    Uses FFmpeg's select filter with scene change detection threshold.

    Returns:
        List of scene dicts with start_time and duration.
    """
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", "select='gt(scene,0.3)',showinfo",
        "-f", "null", "-",
    ]

    try:
        _, stderr = await run_ffmpeg(cmd, retries=0, timeout=120)
    except Exception as e:
        log.warning("scene_detection_failed", error=str(e))
        return []

    scenes = []
    import re
    for line in stderr.split("\n"):
        if "pts_time:" in line:
            match = re.search(r"pts_time:([\d.]+)", line)
            if match:
                scenes.append({
                    "timestamp": round(float(match.group(1)), 3),
                })

    # Convert timestamps to scenes with durations
    result = []
    for i, scene in enumerate(scenes):
        start = scene["timestamp"]
        end = scenes[i + 1]["timestamp"] if i + 1 < len(scenes) else None
        result.append({
            "start": start,
            "duration": round(end - start, 3) if end else None,
        })

    return result


async def _analyze_audio(video_path: str) -> dict:
    """Analyze audio characteristics using librosa.

    Extracts: tempo, spectral centroid, RMS energy, speech ratio.

    Returns:
        Dict with audio analysis metrics.
    """
    # Extract audio to temp WAV file using FFmpeg
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-ac", "1", "-ar", "22050",
        "-t", "120",  # Analyze first 2 minutes max
        tmp_path,
    ]

    try:
        await run_ffmpeg(cmd, retries=0, timeout=60)
    except Exception as e:
        log.warning("audio_extraction_failed", error=str(e))
        return {}

    try:
        result = await asyncio.to_thread(_librosa_analyze, tmp_path)
        return result
    except Exception as e:
        log.warning("librosa_analysis_failed", error=str(e))
        return {}
    finally:
        import os
        os.unlink(tmp_path)


def _librosa_analyze(wav_path: str) -> dict:
    """Run librosa analysis on a WAV file (blocking, run in thread).

    Args:
        wav_path: Path to the WAV audio file.

    Returns:
        Dict with tempo, spectral_centroid_mean, rms_mean, dynamic_range.
    """
    import librosa

    y, sr = librosa.load(wav_path, sr=22050, mono=True)

    # Tempo (BPM)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0])

    # Spectral centroid — brightness of audio
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    centroid_mean = float(np.mean(spectral_centroid))

    # RMS energy — loudness
    rms = librosa.feature.rms(y=y)
    rms_mean = float(np.mean(rms))
    rms_max = float(np.max(rms))
    rms_min = float(np.min(rms[rms > 0])) if np.any(rms > 0) else 0.0

    # Dynamic range
    dynamic_range = round(20 * np.log10(rms_max / rms_min), 1) if rms_min > 0 else 0.0

    return {
        "tempo_bpm": round(tempo_val, 1),
        "spectral_centroid_mean": round(centroid_mean, 1),
        "rms_mean": round(rms_mean, 6),
        "dynamic_range_db": dynamic_range,
    }
