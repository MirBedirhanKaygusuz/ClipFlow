"""Music track management endpoints."""

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aiofiles
import structlog
from fastapi import APIRouter, Header, Request

from app.config import settings
from app.exceptions import ClipFlowError, FFmpegError

router = APIRouter()
log = structlog.get_logger()

# V1: in-memory store — V2: persist to DB
track_store: dict[str, dict] = {}

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg"}


class TrackNotFoundError(ClipFlowError):
    """Raised when the requested music track does not exist."""

    def __init__(self, track_id: str) -> None:
        """Initialise with the missing track ID.

        Args:
            track_id: The track ID that was not found.
        """
        super().__init__(f"Track not found: {track_id}", 404)


def _music_dir() -> Path:
    """Return (and create) the music storage subdirectory.

    Returns:
        Absolute Path to the music storage directory.
    """
    music_path = Path(settings.storage_path) / "music"
    music_path.mkdir(parents=True, exist_ok=True)
    return music_path


@router.post("/music/upload", status_code=201)
async def upload_music(
    request: Request,
    x_filename: Optional[str] = Header(default="track.mp3"),
) -> dict:
    """Upload a music file as raw binary.

    The file is stored in <storage_path>/music/ and an in-memory track
    record is created.

    Args:
        request: Raw HTTP request — body is the binary audio file.
        x_filename: Original filename supplied by the client via the
            ``X-Filename`` header.  The extension is used to derive the
            stored filename; defaults to ``track.mp3``.

    Returns:
        Dict with ``track_id``, ``filename``, and ``size_mb``.

    Raises:
        ClipFlowError: If the extension is not in the allowed set.
    """
    filename = x_filename or "track.mp3"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise ClipFlowError(
            f"Unsupported audio format '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
            400,
        )

    track_id = str(uuid4())
    dest_path = _music_dir() / f"{track_id}{ext}"

    size = 0
    async with aiofiles.open(dest_path, "wb") as f:
        async for chunk in request.stream():
            size += len(chunk)
            await f.write(chunk)

    track_store[track_id] = {
        "track_id": track_id,
        "filename": filename,
        "ext": ext,
        "path": str(dest_path),
        "size_mb": round(size / 1024 / 1024, 2),
        "uploaded_at": datetime.utcnow().isoformat(),
        "beats": None,
        "tempo_bpm": None,
        "duration_seconds": None,
    }
    log.info("music_uploaded", track_id=track_id, filename=filename, size_mb=track_store[track_id]["size_mb"])
    return {
        "track_id": track_id,
        "filename": filename,
        "size_mb": track_store[track_id]["size_mb"],
    }


@router.get("/music")
async def list_tracks() -> list[dict]:
    """Return all uploaded music tracks.

    Returns:
        List of track records ordered by upload time (newest first).
        The ``path`` field is excluded from the response.
    """
    tracks = sorted(
        track_store.values(),
        key=lambda t: t["uploaded_at"],
        reverse=True,
    )
    # Exclude internal file path from API response
    return [{k: v for k, v in t.items() if k != "path"} for t in tracks]


@router.post("/music/{track_id}/analyze")
async def analyze_track(track_id: str) -> dict:
    """Analyze a music track to extract tempo and beat timestamps.

    Uses FFmpeg ``astats`` and ``ebur128`` filters to measure audio
    characteristics, then applies a simple peak-detection heuristic via
    ``ashowinfo`` frame timestamps to estimate beat positions.

    Args:
        track_id: UUID of the track to analyze.

    Returns:
        Dict containing ``track_id``, ``tempo_bpm``, ``beat_count``,
        ``beats`` (list of float timestamps in seconds), and
        ``duration_seconds``.

    Raises:
        TrackNotFoundError: If the track_id is not in the store.
        FFmpegError: If FFmpeg fails during analysis.
    """
    if track_id not in track_store:
        raise TrackNotFoundError(track_id)

    track = track_store[track_id]
    file_path = track["path"]

    # --- Step 1: Get duration via ffprobe ---
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        probe_result = await asyncio.to_thread(
            subprocess.run,
            probe_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError("ffprobe timed out") from exc

    if probe_result.returncode != 0:
        raise FFmpegError(probe_result.stderr)

    try:
        duration_seconds = float(probe_result.stdout.strip())
    except ValueError:
        duration_seconds = None

    # --- Step 2: Extract beat timestamps via FFmpeg silencedetect on the
    #     inverted signal.  We use a tempo-estimation heuristic: split the
    #     track into 512-sample frames, compute RMS via astats, and collect
    #     the frame pts values where the RMS crosses a threshold. This is a
    #     lightweight approximation; replace with librosa in V2 for accuracy.
    beat_cmd = [
        "ffmpeg",
        "-i", file_path,
        "-af", (
            "aresample=22050,"           # downsample for speed
            "asetnsamples=512,"          # fixed frame size
            "astats=metadata=1:reset=1," # per-frame stats in metadata
            "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-"
        ),
        "-f", "null",
        "-",
    ]
    try:
        beat_result = await asyncio.to_thread(
            subprocess.run,
            beat_cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError("ffmpeg beat analysis timed out") from exc

    # Parse RMS metadata lines: "pts_time:N|lavfi.astats.Overall.RMS_level=V"
    beats: list[float] = []
    rms_values: list[tuple[float, float]] = []  # (pts_time, rms_db)

    for line in beat_result.stderr.splitlines():
        # ametadata outputs to stderr via "file=-"
        if "lavfi.astats.Overall.RMS_level=" in line:
            try:
                rms_str = line.split("=", 1)[1]
                rms_db = float(rms_str)
                # pts_time appears on the preceding line; we parse both together
                rms_values.append(rms_db)
            except (ValueError, IndexError):
                continue

    # Also check stdout for ametadata output
    for line in beat_result.stdout.splitlines():
        if "pts_time" in line and "lavfi.astats.Overall.RMS_level" in line:
            try:
                parts = line.split("|")
                pts_time = float(parts[0].split("pts_time:")[1])
                rms_db = float(parts[1].split("=")[1])
                rms_values_with_pts = True
                beats_candidate = (pts_time, rms_db)
            except (ValueError, IndexError):
                continue

    # Simple peak-threshold beat detection on RMS values
    # This produces a rough BPM estimate suitable for V1 sync features
    if rms_values:
        max_rms = max(rms_values)
        threshold = max_rms - 6.0  # 6 dB below peak
        frame_duration = 512 / 22050  # seconds per frame

        in_beat = False
        for idx, rms in enumerate(rms_values):
            pts = idx * frame_duration
            if rms >= threshold and not in_beat:
                beats.append(round(pts, 3))
                in_beat = True
            elif rms < threshold - 3.0:
                in_beat = False

    # Estimate BPM from average inter-beat interval
    tempo_bpm: float | None = None
    if len(beats) >= 2 and duration_seconds and duration_seconds > 0:
        intervals = [beats[i + 1] - beats[i] for i in range(len(beats) - 1)]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval > 0:
            tempo_bpm = round(60.0 / avg_interval, 1)

    # Update in-memory record
    track_store[track_id].update(
        {
            "beats": beats,
            "tempo_bpm": tempo_bpm,
            "duration_seconds": duration_seconds,
        }
    )

    log.info(
        "music_analyzed",
        track_id=track_id,
        tempo_bpm=tempo_bpm,
        beat_count=len(beats),
        duration_seconds=duration_seconds,
    )

    return {
        "track_id": track_id,
        "tempo_bpm": tempo_bpm,
        "beat_count": len(beats),
        "beats": beats,
        "duration_seconds": duration_seconds,
    }
