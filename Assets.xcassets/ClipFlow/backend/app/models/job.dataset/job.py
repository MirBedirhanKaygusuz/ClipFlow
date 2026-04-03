"""Pydantic models for job processing."""

from pydantic import BaseModel
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    AWAITING_DECISION = "awaiting_decision"
    DONE = "done"
    FAILED = "failed"


class ProcessRequest(BaseModel):
    clip_ids: list[str]
    mode: str = "talking_reels"
    quality: str = "reels"
    settings: dict = {"output_format": "9:16", "add_captions": True}
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
    eta_seconds: float | None = None
