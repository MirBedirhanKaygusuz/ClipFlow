"""Pydantic models for job processing."""

from pydantic import BaseModel
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    AWAITING_DECISION = "awaiting_decision"
    DONE = "done"
    FAILED = "failed"


class QualityMode(str, Enum):
    """Video output quality preset."""
    REELS = "reels"             # 1080x1920, 10Mbps, 30fps — Instagram optimized
    HIGH_QUALITY = "high_quality"  # Original resolution, CRF 17 — visually lossless


class ProcessSettings(BaseModel):
    """Optional processing settings from iOS client."""

    output_format: str = "9:16"
    add_captions: bool = False
    enable_zoom: bool = False
    zoom_intensity: float = 0.5
    transition: str = "fade"
    transition_duration: float = 0.5
    music_file_id: str | None = None


class ProcessRequest(BaseModel):
    clip_ids: list[str]
    mode: str = "talking_reels"
    quality: QualityMode = QualityMode.REELS
    settings: ProcessSettings = ProcessSettings()
    device_token: str | None = None


class ProcessResponse(BaseModel):
    job_id: str
    estimated_seconds: int


class StatusResponse(BaseModel):
    status: JobStatus
    progress: int = 0
    step: str = ""
    output_url: str | None = None
    question: str | None = None
    options: list[str] | None = None
    stats: dict | None = None
    eta_seconds: int | None = None
