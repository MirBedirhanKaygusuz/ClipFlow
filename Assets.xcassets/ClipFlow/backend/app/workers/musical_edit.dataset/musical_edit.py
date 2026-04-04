"""Musical Edit pipeline — beat-synced video editing with transitions."""

import asyncio
import time
import structlog
from pathlib import Path

from app.models.job import ProcessRequest, JobStatus
from app.services.job_manager import job_store
from app.services.beat_detector import detect_beats, detect_beats_from_music
from app.services.highlight_detector import detect_highlights
from app.services.format_converter import convert_to_vertical
from app.services.ffmpeg_runner import run_ffmpeg
from app.services.push_notification import notify_job_complete, notify_job_failed
from app.config import settings

log = structlog.get_logger()


async def process_musical_edit(job_id: str, request: ProcessRequest) -> None:
    """Main pipeline for musical edit mode.

    Pipeline:
    1. Detect beats in the music track
    2. Detect highlights in the video
    3. Align highlight clips to beat positions
    4. Concatenate with crossfade transitions
    5. Mix with music track
    6. Optional format conversion (9:16)

    Args:
        job_id: Unique job identifier.
        request: Processing request. Settings should include:
            - music_file_id: ID of uploaded music file
            - transition: Transition type (default: "xfade")
            - transition_duration: Duration in seconds (default: 0.5)
    """
    temp_files = []

    try:
        job = job_store[job_id]
        job["status"] = JobStatus.PROCESSING

        await asyncio.wait_for(
            _run_musical_pipeline(job_id, request, job, temp_files),
            timeout=settings.processing_timeout,
        )

        await notify_job_complete(
            request.device_token, job_id, job_store[job_id].get("stats")
        )

    except asyncio.TimeoutError:
        log.error("musical_pipeline_timeout", job_id=job_id)
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["step"] = "error: İşlem zaman aşımına uğradı"
        await notify_job_failed(request.device_token, job_id, "timeout")

    except Exception as e:
        log.error("musical_pipeline_failed", job_id=job_id, error=str(e))
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["step"] = f"error: {str(e)[:100]}"
        await notify_job_failed(request.device_token, job_id, str(e)[:100])

    finally:
        for f in temp_files:
            Path(f).unlink(missing_ok=True)


async def _run_musical_pipeline(
    job_id: str,
    request: ProcessRequest,
    job: dict,
    temp_files: list[str],
) -> None:
    """Execute the musical edit pipeline steps."""
    start_time = time.monotonic()
    storage_path = Path(settings.storage_path)
    req_settings = request.settings or {}
    transition_type = req_settings.get("transition", "fade")
    transition_duration = float(req_settings.get("transition_duration", 0.5))

    def _update_eta(progress: int) -> None:
        if progress <= 0:
            return
        elapsed = time.monotonic() - start_time
        total_est = elapsed / (progress / 100)
        job["eta_seconds"] = round(total_est - elapsed, 1)

    # Step 1: Analyze music beats
    job["step"] = "beat_detection"
    job["progress"] = 10
    _update_eta(10)
    log.info("musical_step", job_id=job_id, step="beat_detection")

    music_file_id = req_settings.get("music_file_id")
    if music_file_id:
        music_path = storage_path / f"{music_file_id}.mp4"
        beats = await detect_beats_from_music(str(music_path))
    else:
        # Use video's own audio for beat detection
        video_path = storage_path / f"{request.clip_ids[0]}.mp4"
        beats = await detect_beats(str(video_path))

    beat_times = beats.get("beat_times", [])
    tempo = beats.get("tempo", 120)
    log.info("beats_found", tempo=tempo, count=len(beat_times))

    # Step 2: Detect highlights in video
    job["step"] = "highlight_detection"
    job["progress"] = 30
    _update_eta(30)
    log.info("musical_step", job_id=job_id, step="highlight_detection")

    video_path = storage_path / f"{request.clip_ids[0]}.mp4"
    highlights = await detect_highlights(
        str(video_path),
        max_highlights=len(beat_times) // 2 if beat_times else 10,
        min_duration=0.5,
        max_duration=60 / tempo * 4 if tempo > 0 else 4.0,  # 4 beats worth
    )

    if not highlights:
        # Fallback: use evenly spaced segments
        duration = beats.get("duration", 30)
        segment_len = duration / max(len(beat_times) // 4, 1)
        highlights = [
            {"start": round(i * segment_len, 2), "end": round((i + 1) * segment_len, 2), "score": 0.5}
            for i in range(min(len(beat_times) // 4, 10))
        ]

    # Step 3: Align clips to beats
    job["step"] = "beat_sync"
    job["progress"] = 50
    _update_eta(50)
    log.info("musical_step", job_id=job_id, step="beat_sync", highlights=len(highlights))

    aligned_clips = _align_to_beats(highlights, beat_times)

    # Step 4: Build the edit with transitions
    job["step"] = "rendering"
    job["progress"] = 60
    _update_eta(60)
    log.info("musical_step", job_id=job_id, step="rendering")

    rendered_path = storage_path / f"{job_id}_rendered.mp4"
    temp_files.append(str(rendered_path))

    await _render_clips(
        video_path=str(video_path),
        clips=aligned_clips,
        output_path=str(rendered_path),
        transition_type=transition_type,
        transition_duration=transition_duration,
    )

    # Step 5: Mix with music (if separate music track)
    mixed_path = storage_path / f"{job_id}_mixed.mp4"
    temp_files.append(str(mixed_path))

    if music_file_id:
        job["step"] = "music_mixing"
        job["progress"] = 80
        _update_eta(80)
        log.info("musical_step", job_id=job_id, step="music_mixing")

        music_path = storage_path / f"{music_file_id}.mp4"
        await _mix_audio(str(rendered_path), str(music_path), str(mixed_path))
    else:
        mixed_path = rendered_path

    # Step 6: Format conversion
    output_path = storage_path / f"{job_id}_final.mp4"

    if request.quality == "reels":
        job["step"] = "format_conversion"
        job["progress"] = 90
        _update_eta(90)
        await convert_to_vertical(str(mixed_path), str(output_path))
    else:
        import shutil
        shutil.copy2(str(mixed_path), str(output_path))

    # Done
    job["status"] = JobStatus.DONE
    job["progress"] = 100
    job["eta_seconds"] = None
    job["step"] = "done"
    job["output_url"] = f"/api/v1/download/{job_id}_final"
    job["stats"] = {
        "tempo": tempo,
        "beat_count": len(beat_times),
        "highlight_count": len(highlights),
        "clip_count": len(aligned_clips),
        "transition": transition_type,
        "duration": beats.get("duration", 0),
    }
    log.info("musical_pipeline_done", job_id=job_id, stats=job["stats"])


def _align_to_beats(
    highlights: list[dict],
    beat_times: list[float],
) -> list[dict]:
    """Align highlight clips to beat positions.

    Each highlight gets snapped so its start aligns with the nearest beat.

    Args:
        highlights: Detected highlight segments.
        beat_times: List of beat timestamps.

    Returns:
        List of aligned clip dicts with start, end, and beat_aligned_start.
    """
    if not beat_times:
        return highlights

    aligned = []
    used_beats = set()

    for h in highlights:
        # Find nearest unused beat to this highlight's start
        best_beat = None
        best_dist = float("inf")
        for i, bt in enumerate(beat_times):
            if i not in used_beats:
                dist = abs(h["start"] - bt)
                if dist < best_dist:
                    best_dist = dist
                    best_beat = i

        if best_beat is not None:
            used_beats.add(best_beat)
            clip_duration = h["end"] - h["start"]
            aligned.append({
                "start": h["start"],
                "end": h["end"],
                "duration": round(clip_duration, 3),
                "beat_time": beat_times[best_beat],
                "score": h.get("score", 0),
            })

    # Sort by beat time for chronological playback
    aligned.sort(key=lambda x: x["beat_time"])
    return aligned


async def _render_clips(
    video_path: str,
    clips: list[dict],
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = 0.5,
) -> None:
    """Render clips with transitions using FFmpeg filter_complex.

    Args:
        video_path: Source video path.
        clips: List of clip dicts with start/end times.
        output_path: Destination path.
        transition_type: FFmpeg xfade transition name.
        transition_duration: Transition duration in seconds.
    """
    if not clips:
        return

    if len(clips) == 1:
        # Single clip, no transitions needed
        c = clips[0]
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(c["start"]),
            "-t", str(c["duration"]),
            "-c:v", "libx264", "-preset", settings.ffmpeg_preset,
            "-c:a", "aac",
            output_path,
        ]
        await run_ffmpeg(cmd, retries=1, timeout=300)
        return

    # Build filter_complex for multiple clips with xfade
    filter_parts = []

    # Trim each clip
    for i, c in enumerate(clips):
        filter_parts.append(
            f"[0:v]trim=start={c['start']:.3f}:end={c['end']:.3f},"
            f"setpts=PTS-STARTPTS[v{i}]"
        )
        filter_parts.append(
            f"[0:a]atrim=start={c['start']:.3f}:end={c['end']:.3f},"
            f"asetpts=PTS-STARTPTS[a{i}]"
        )

    # Apply xfade transitions between consecutive clips
    if len(clips) > 1:
        # Chain xfade for video
        prev_v = "v0"
        for i in range(1, len(clips)):
            out_label = f"xv{i}" if i < len(clips) - 1 else "outv"
            offset = max(0, clips[i - 1]["duration"] - transition_duration)
            # Accumulate offsets from previous transitions
            for j in range(1, i):
                offset += max(0, clips[j]["duration"] - transition_duration)

            filter_parts.append(
                f"[{prev_v}][v{i}]xfade=transition={transition_type}:"
                f"duration={transition_duration:.2f}:offset={offset:.3f}[{out_label}]"
            )
            prev_v = out_label

        # Chain acrossfade for audio
        prev_a = "a0"
        for i in range(1, len(clips)):
            out_label = f"xa{i}" if i < len(clips) - 1 else "outa"
            filter_parts.append(
                f"[{prev_a}][a{i}]acrossfade=d={transition_duration:.2f}[{out_label}]"
            )
            prev_a = out_label
    else:
        filter_parts.append("[v0]copy[outv]")
        filter_parts.append("[a0]acopy[outa]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", settings.ffmpeg_preset,
        "-c:a", "aac",
        output_path,
    ]
    await run_ffmpeg(cmd, retries=1, timeout=300)


async def _mix_audio(
    video_path: str,
    music_path: str,
    output_path: str,
    video_volume: float = 0.3,
    music_volume: float = 0.7,
) -> None:
    """Mix video's original audio with a music track.

    Args:
        video_path: Video with original audio.
        music_path: Music track to mix in.
        output_path: Output file path.
        video_volume: Volume level for original audio (0-1).
        music_volume: Volume level for music (0-1).
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex",
        f"[0:a]volume={video_volume}[va];"
        f"[1:a]volume={music_volume}[ma];"
        f"[va][ma]amix=inputs=2:duration=shortest[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    await run_ffmpeg(cmd, retries=1, timeout=300)
