"""Talking Reels pipeline — silence removal + quality-aware encoding."""

import asyncio
from pathlib import Path

import structlog

from app.config import settings
from app.models.job import ProcessRequest, JobStatus, QualityMode
from app.services.format_converter import encode_output
from app.services.job_manager import job_store
from app.services.silence_detector import detect_silence, cut_silences

log = structlog.get_logger()


async def process_talking_reels(job_id: str, request: ProcessRequest) -> None:
    """Main pipeline for talking reels mode.

    Pipeline varies by quality:
        REELS:        detect → cut (intermediate) → encode_reels (1080x1920)
        HIGH_QUALITY: detect → cut (final CRF 17) → done (no second encode)

    Args:
        job_id: Unique job identifier.
        request: ProcessRequest with clip_ids and quality mode.
    """
    try:
        job = job_store[job_id]
        job["status"] = JobStatus.PROCESSING
        job["eta_seconds"] = None
        quality = request.quality

        # Step 1: Silence detection
        job["step"] = "silence_detection"
        job["progress"] = 10
        job["eta_seconds"] = 60
        log.info("pipeline_step", job_id=job_id, step="silence_detection", quality=quality.value)

        # Find the uploaded file — extension may be .mp4, .mov, or .m4v
        clip_id = request.clip_ids[0]
        storage_dir = Path(settings.storage_path)
        input_path = next(
            (p for ext in (".mp4", ".mov", ".m4v") if (p := storage_dir / f"{clip_id}{ext}").exists()),
            storage_dir / f"{clip_id}.mp4",
        )

        silences = await asyncio.to_thread(detect_silence, str(input_path))

        # Step 2: Cut silences
        job["step"] = "cutting"
        job["progress"] = 40
        job["eta_seconds"] = 40
        log.info("pipeline_step", job_id=job_id, step="cutting", silence_count=len(silences))

        cut_path = storage_dir / f"{job_id}_cut.mp4"
        stats = await asyncio.to_thread(
            cut_silences, str(input_path), str(cut_path), silences, quality,
        )

        # Step 3: Format encoding (only for reels — high_quality is already final)
        if quality == QualityMode.REELS:
            job["step"] = "format_conversion"
            job["progress"] = 70
            job["eta_seconds"] = 20
            log.info("pipeline_step", job_id=job_id, step="format_conversion")

            output_path = storage_dir / f"{job_id}_final.mp4"
            await asyncio.to_thread(encode_output, str(cut_path), str(output_path), quality)
        else:
            # High quality: cut output IS the final output
            output_path = cut_path
            job["progress"] = 90

        # Done
        job["status"] = JobStatus.DONE
        job["progress"] = 100
        job["step"] = "done"
        job["output_url"] = f"/api/v1/download/{output_path.stem}"
        job["stats"] = stats
        log.info("pipeline_done", job_id=job_id, quality=quality.value, stats=stats)

    except Exception as e:
        log.error("pipeline_failed", job_id=job_id, error=str(e))
        job_store[job_id]["status"] = JobStatus.FAILED
        job_store[job_id]["step"] = f"error: {str(e)[:100]}"
