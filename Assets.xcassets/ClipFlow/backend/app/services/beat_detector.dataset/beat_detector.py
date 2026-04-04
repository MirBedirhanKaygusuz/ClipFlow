"""Beat detection and music analysis using librosa."""

import asyncio
import tempfile
import os
import structlog
import numpy as np

from app.services.ffmpeg_runner import run_ffmpeg

log = structlog.get_logger()


async def detect_beats(audio_path: str) -> dict:
    """Detect beats and musical structure from an audio/video file.

    Args:
        audio_path: Path to audio or video file.

    Returns:
        Dict with tempo, beat_times, downbeat_times, and beat_count.
    """
    # Extract audio to WAV for librosa
    wav_path = await _extract_audio(audio_path)

    try:
        result = await asyncio.to_thread(_librosa_beat_detection, wav_path)
        log.info(
            "beats_detected",
            tempo=result["tempo"],
            beat_count=result["beat_count"],
        )
        return result
    finally:
        os.unlink(wav_path)


async def detect_beats_from_music(music_path: str) -> dict:
    """Detect beats from a standalone music file.

    Same as detect_beats but optimized for music files (no video extraction needed).

    Args:
        music_path: Path to the music file (mp3, wav, etc.).

    Returns:
        Dict with tempo, beat_times, downbeat_times, and segments.
    """
    # If it's already WAV, use directly; otherwise extract
    if music_path.endswith(".wav"):
        return await asyncio.to_thread(_librosa_beat_detection, music_path)

    wav_path = await _extract_audio(music_path)
    try:
        return await asyncio.to_thread(_librosa_beat_detection, wav_path)
    finally:
        os.unlink(wav_path)


async def _extract_audio(input_path: str) -> str:
    """Extract audio from video/audio file to mono WAV.

    Args:
        input_path: Source file path.

    Returns:
        Path to the extracted WAV file.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "22050",
        "-vn",  # No video
        tmp_path,
    ]
    await run_ffmpeg(cmd, retries=0, timeout=120)
    return tmp_path


def _librosa_beat_detection(wav_path: str) -> dict:
    """Run librosa beat detection on a WAV file (blocking).

    Args:
        wav_path: Path to mono WAV file.

    Returns:
        Dict with tempo, beat_times, downbeat_times, beat_count,
        onset_times, and energy_curve.
    """
    import librosa

    y, sr = librosa.load(wav_path, sr=22050, mono=True)
    duration = len(y) / sr

    # Beat tracking
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    # Onset detection (more precise than beats for cut points)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()

    # Onset strength envelope (energy curve for visualization)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_env_normalized = (onset_env / onset_env.max()).tolist() if onset_env.max() > 0 else []

    # Downbeats (every 4th beat for 4/4 time)
    downbeat_times = beat_times[::4] if len(beat_times) >= 4 else beat_times

    # Musical segments via spectral clustering
    segments = _detect_segments(y, sr)

    return {
        "tempo": round(tempo_val, 1),
        "beat_times": [round(t, 3) for t in beat_times],
        "beat_count": len(beat_times),
        "downbeat_times": [round(t, 3) for t in downbeat_times],
        "onset_times": [round(t, 3) for t in onset_times],
        "energy_curve_length": len(onset_env_normalized),
        "segments": segments,
        "duration": round(duration, 2),
    }


def _detect_segments(y: np.ndarray, sr: int) -> list[dict]:
    """Detect musical segments (intro, verse, chorus, etc.) using spectral features.

    Args:
        y: Audio signal.
        sr: Sample rate.

    Returns:
        List of segments with start, end, and energy level.
    """
    import librosa

    # Use RMS energy to find segment boundaries
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)

    # Simple energy-based segmentation: split into chunks and classify
    chunk_duration = 4.0  # 4-second chunks
    duration = len(y) / sr
    segments = []

    i = 0.0
    while i < duration:
        end = min(i + chunk_duration, duration)

        # Get average energy for this chunk
        mask = (rms_times >= i) & (rms_times < end)
        chunk_energy = float(np.mean(rms[mask])) if np.any(mask) else 0.0

        segments.append({
            "start": round(i, 2),
            "end": round(end, 2),
            "energy": round(chunk_energy, 6),
        })
        i = end

    return segments
