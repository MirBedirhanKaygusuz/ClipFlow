"""Enhanced progress tracking for the video processing pipeline.

ProgressTracker wraps the in-memory job_store with structured updates so every
stage of the pipeline (upload, scene detection, silence removal, encoding …)
can report granular progress, sub-step details, and an estimated time remaining.

All public methods are synchronous — they only mutate the in-memory dict and
never perform I/O — so there is no need for async here.  Callers in async
contexts can call them directly without ``await``.

Typical usage::

    tracker = ProgressTracker(job_id="abc123", total_steps=4)
    tracker.update(step=1, progress=0.25, eta_seconds=60)
    tracker.add_substep("silence_detection", "Found 3 silent segments")
    tracker.update(step=2, progress=0.50)
    tracker.complete(output_url="https://…/output.mp4", stats={"segments": 3})
"""

import time
from typing import Any

import structlog

from app.exceptions import JobNotFoundError
from app.services.job_manager import job_store

logger: structlog.BoundLogger = structlog.get_logger(__name__)


class ProgressTracker:
    """Structured progress reporter that writes into job_store for a single job.

    Args:
        job_id: The job identifier.  Must already exist in job_store when this
            tracker is created.
        total_steps: Total number of major pipeline steps (used for overall
            progress calculation).  Defaults to 1.

    Raises:
        JobNotFoundError: If job_id is not present in job_store at
            construction time.
    """

    def __init__(self, job_id: str, total_steps: int = 1) -> None:
        if job_id not in job_store:
            raise JobNotFoundError(job_id)

        self._job_id: str = job_id
        self._total_steps: int = max(total_steps, 1)
        self._start_time: float = time.monotonic()

        # Initialise tracker-specific keys if not already present
        job = job_store[job_id]
        job.setdefault("progress", 0.0)
        job.setdefault("current_step", 0)
        job.setdefault("total_steps", self._total_steps)
        job.setdefault("eta_seconds", None)
        job.setdefault("step_history", [])
        job.setdefault("status", "processing")

        logger.info("tracker.init", job_id=job_id, total_steps=total_steps)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _calculate_eta(self, progress: float) -> float | None:
        """Estimate seconds remaining based on elapsed time and current progress.

        Uses a simple linear extrapolation: if ``progress`` fraction of work
        has been done in ``elapsed`` seconds, the remainder should take
        ``elapsed * (1 - progress) / progress`` seconds.

        Args:
            progress: Fractional completion in the range [0.0, 1.0].

        Returns:
            float | None: Estimated seconds remaining, or None if progress is
                zero (division by zero guard).
        """
        if progress <= 0.0:
            return None
        elapsed = time.monotonic() - self._start_time
        return elapsed * (1.0 - progress) / progress

    def _job(self) -> dict[str, Any]:
        """Return the mutable job dict from job_store.

        Returns:
            dict[str, Any]: The live job dict.

        Raises:
            JobNotFoundError: If the job was evicted from job_store since
                the tracker was created (shouldn't happen in V1, but defensive).
        """
        if self._job_id not in job_store:
            raise JobNotFoundError(self._job_id)
        return job_store[self._job_id]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        step: int,
        progress: float,
        eta_seconds: float | None = None,
    ) -> None:
        """Record current pipeline step and overall progress fraction.

        The ``progress`` value is clamped to [0.0, 1.0].  If ``eta_seconds``
        is not supplied it is calculated automatically from elapsed time.

        Args:
            step: The current major step index (1-based).
            progress: Fractional overall completion (0.0 = start, 1.0 = done).
            eta_seconds: Explicit ETA override in seconds.  When omitted the
                tracker estimates it from elapsed time and ``progress``.

        Raises:
            JobNotFoundError: If the job is no longer in job_store.
        """
        progress = max(0.0, min(1.0, progress))
        computed_eta = eta_seconds if eta_seconds is not None else self._calculate_eta(progress)

        job = self._job()
        job["current_step"] = step
        job["progress"] = round(progress, 4)
        job["eta_seconds"] = round(computed_eta, 1) if computed_eta is not None else None
        job["status"] = "processing"

        logger.info(
            "tracker.update",
            job_id=self._job_id,
            step=step,
            progress=job["progress"],
            eta_seconds=job["eta_seconds"],
        )

    def add_substep(self, name: str, detail: str) -> None:
        """Append a named sub-step entry to the job's step history.

        Sub-steps let the polling endpoint expose fine-grained pipeline events
        (e.g. "Detected 5 scenes", "Removed 12.3 s of silence") without
        changing the top-level progress value.

        Args:
            name: Short identifier for the sub-step (e.g. ``"scene_detect"``).
            detail: Human-readable description of what happened.

        Raises:
            JobNotFoundError: If the job is no longer in job_store.
        """
        entry: dict[str, Any] = {
            "name": name,
            "detail": detail,
            "timestamp": round(time.monotonic() - self._start_time, 3),
        }
        job = self._job()
        job["step_history"].append(entry)

        logger.info("tracker.substep", job_id=self._job_id, name=name, detail=detail)

    def complete(self, output_url: str, stats: dict[str, Any]) -> None:
        """Mark the job as successfully completed.

        Sets ``status`` to ``"done"``, records the output URL, clears the ETA,
        and stores the final processing statistics.

        Args:
            output_url: URL (or local path) where the processed video can be
                retrieved by the iOS client.
            stats: Arbitrary stats dict produced by the pipeline
                (e.g. ``{"duration_s": 30.4, "segments_removed": 4}``).

        Raises:
            JobNotFoundError: If the job is no longer in job_store.
        """
        job = self._job()
        elapsed = time.monotonic() - self._start_time

        job["status"] = "done"
        job["progress"] = 1.0
        job["eta_seconds"] = 0
        job["output_url"] = output_url
        job["stats"] = stats
        job["elapsed_seconds"] = round(elapsed, 2)

        logger.info(
            "tracker.complete",
            job_id=self._job_id,
            elapsed_seconds=job["elapsed_seconds"],
            output_url=output_url,
        )

    def fail(self, error_msg: str) -> None:
        """Mark the job as failed and record the error message.

        Sets ``status`` to ``"error"`` and preserves whatever progress was
        reached before the failure.

        Args:
            error_msg: Human-readable description of what went wrong.  Stored
                verbatim; callers should truncate if necessary.

        Raises:
            JobNotFoundError: If the job is no longer in job_store.
        """
        job = self._job()
        elapsed = time.monotonic() - self._start_time

        job["status"] = "error"
        job["error"] = error_msg
        job["eta_seconds"] = None
        job["elapsed_seconds"] = round(elapsed, 2)

        logger.error(
            "tracker.fail",
            job_id=self._job_id,
            error=error_msg,
            elapsed_seconds=job["elapsed_seconds"],
        )
