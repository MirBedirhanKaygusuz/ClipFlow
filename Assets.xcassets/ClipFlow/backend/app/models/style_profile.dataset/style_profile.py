"""Pydantic models for style profiles."""

from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


class AudioProfile(BaseModel):
    """Audio characteristics of a style."""

    tempo_bpm: float | None = None
    spectral_centroid_mean: float | None = None
    rms_mean: float | None = None
    dynamic_range_db: float | None = None


class StyleProfile(BaseModel):
    """Complete style profile extracted from a video."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = "Untitled Style"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Video characteristics
    duration: float = 0
    scene_count: int = 0
    avg_scene_duration: float = 0
    cut_frequency: float = 0  # cuts per minute
    resolution: str | None = None
    fps: float | None = None

    # Audio characteristics
    audio: AudioProfile = Field(default_factory=AudioProfile)

    # Raw scene data (timestamps)
    scenes: list[dict] = Field(default_factory=list)


class StyleProfileCreate(BaseModel):
    """Request body for creating a style profile from analysis."""

    name: str
    video_file_id: str


class StyleProfileUpdate(BaseModel):
    """Request body for updating a style profile."""

    name: str | None = None
