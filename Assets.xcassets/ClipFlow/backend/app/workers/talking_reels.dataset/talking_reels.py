"""Talking Reels pipeline — silence removal + format conversion."""

import asyncio
import shutil
import time
import structlog
from app.models.job import ProcessRequest, JobStatus
from app.services.job_manager import job_store
from app.services.silence_detector import detect_silence, cut_silences
from app.services.format_converter import convert_to_vertical
from app.services.zoom_analyzer import analyze_zoom_keyframes
from app.services.push_notification import notify_job_complete, notify_job_failed
from app.config import settings
from pathlib import Path

log = structlog.get_logger()


async def process_talking_reels(job_id: str, request: ProcessRequest) -> None:
    """Main pipeline for talking reels mode.

    Args:
        job_id: Unique job identifier.
        request: Processing request with clip_ids, quality, and settings.
    """
    cut_path = Path(settings.storage_path) / f"{job_id}_cut.mp4"

    try:
        job = job_store[job_id]
        job["status"] = JobStatus.PROCESSING

        # Wrap entire pipeline with timeout
        await asyncio.wait_for(
            _run_pipeline(job_id, request, job, cut_path),
            timeout=settings.processing_timeout,
        )

        # Send push notification on success
        await notify_job_complete(
            request.device_token, job_id, job_store[job_id].get("stats")
        )

    except asyncio.TimeoutError:
        log.error("pipeline_timeout", job_id=job_id)
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["step"] = "error: İşlem zaman aşımına uğradı"
        await notify_job_failed(request.device_token, job_id, "timeout")

    except Exception as e:
        log.error("pipeline_failed", job_id=job_id, error=str(e))
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["step"] = f"error: {str(e)[:100]}"
        await notify_job_failed(request.device_token, job_id, str(e)[:100])

    finally:
        # Clean up intermediate files
        cut_path.unlink(missing_ok=True)


async def _run_pipeline(
    job_id: str,
    request: ProcessRequest,
    job: dict,
    cut_path: Path,
) -> None:
    """Execute the processing pipeline steps.

    Args:
        job_id: Unique job identifier.
        request: Processing request.
        job: Job state dict from job_store.
        cut_path: Path for the intermediate cut file.
    """
    start_time = time.monotonic()

    def _update_eta(progress: int) -> None:
        """Estimate remaining time based on elapsed time and progress."""
        if progress <= 0:
            return
        elapsed = time.monotonic() - start_time
        total_estimated = elapsed / (progress / 100)
        job["eta_seconds"] = round(total_estimated - elapsed, 1)

    # Step 1: Silence detection
    job["step"] = "silence_detection"
    job["progress"] = 10
    _update_eta(10)
    log.info("pipeline_step", job_id=job_id, step="silence_detection")

    input_path = Path(settings.storage_path) / f"{request.clip_ids[0]}.mp4"
    silences = await detect_silence(str(input_path))

    # Step 2: Cut silences
    job["step"] = "cutting"
    job["progress"] = 40
    _update_eta(40)
    log.info(
        "pipeline_step",
        job_id=job_id,
        step="cutting",
        silence_count=len(silences),
    )

    stats = await cut_silences(str(input_path), str(cut_path), silences)

    output_path = Path(settings.storage_path) / f"{job_id}_final.mp4"

    # Step 3: Zoom analysis (if enabled and reels mode)
    zoom_keyframes = None
    req_settings = request.settings or {}
    enable_zoom = req_settings.get("enable_zoom", False)

    if enable_zoom and request.quality == "reels":
        job["step"] = "zoom_analysis"
        job["progress"] = 55
        _update_eta(55)
        log.info("pipeline_step", job_id=job_id, step="zoom_analysis")
        zoom_intensity = float(req_settings.get("zoom_intensity", 0.5))
        zoom_keyframes = await analyze_zoom_keyframes(
            str(cut_path), zoom_intensity=zoom_intensity
        )
        log.info(
            "zoom_analysis_done",
            job_id=job_id,
            keyframe_count=len(zoom_keyframes),
        )

    # Step 4: Format conversion based on quality mode
    if request.quality == "reels":
        job["step"] = "format_conversion"
        job["progress"] = 70
        _update_eta(70)
        log.info("pipeline_step", job_id=job_id, step="format_conversion")
        await convert_to_vertical(str(cut_path), str(output_path), zoom_keyframes)
    else:
        # high_quality: keep original resolution, just use the cut file
        job["step"] = "finalizing"
        job["progress"] = 70
        _update_eta(70)
        log.info(
            "pipeline_step",
            job_id=job_id,
            step="finalizing",
            quality="high_quality",
        )
        shutil.copy2(str(cut_path), str(output_path))

    # Done
    job["status"] = JobStatus.DONE
    job["progress"] = 100
    job["eta_seconds"] = None
    job["step"] = "done"
    job["output_url"] = f"/api/v1/download/{job_id}_final"
    job["stats"] = stats
    log.info("pipeline_done", job_id=job_id, stats=stats)
