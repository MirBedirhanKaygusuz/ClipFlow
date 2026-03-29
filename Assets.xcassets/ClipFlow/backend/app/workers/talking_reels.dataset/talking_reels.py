"""Talking Reels pipeline — silence removal + format conversion."""

import structlog
from app.models.job import ProcessRequest, JobStatus
from app.services.job_manager import job_store
from app.services.silence_detector import detect_silence, cut_silences
from app.services.format_converter import convert_to_vertical
from app.config import settings
from pathlib import Path

log = structlog.get_logger()


async def process_talking_reels(job_id: str, request: ProcessRequest) -> None:
    """Main pipeline for talking reels mode."""
    try:
        job = job_store[job_id]
        job["status"] = JobStatus.PROCESSING

        # Step 1: Silence detection
        job["step"] = "silence_detection"
        job["progress"] = 10
        log.info("pipeline_step", job_id=job_id, step="silence_detection")

        input_path = Path(settings.storage_path) / f"{request.clip_ids[0]}.mp4"
        silences = detect_silence(str(input_path))

        # Step 2: Cut silences
        job["step"] = "cutting"
        job["progress"] = 40
        log.info("pipeline_step", job_id=job_id, step="cutting", silence_count=len(silences))

        cut_path = Path(settings.storage_path) / f"{job_id}_cut.mp4"
        stats = cut_silences(str(input_path), str(cut_path), silences)

        # Step 3: Convert to 9:16
        job["step"] = "format_conversion"
        job["progress"] = 70
        log.info("pipeline_step", job_id=job_id, step="format_conversion")

        output_path = Path(settings.storage_path) / f"{job_id}_final.mp4"
        convert_to_vertical(str(cut_path), str(output_path))

        # Done
        job["status"] = JobStatus.DONE
        job["progress"] = 100
        job["step"] = "done"
        job["output_url"] = f"/api/v1/download/{job_id}_final"
        job["stats"] = stats
        log.info("pipeline_done", job_id=job_id, stats=stats)

    except Exception as e:
        log.error("pipeline_failed", job_id=job_id, error=str(e))
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["step"] = f"error: {str(e)[:100]}"
