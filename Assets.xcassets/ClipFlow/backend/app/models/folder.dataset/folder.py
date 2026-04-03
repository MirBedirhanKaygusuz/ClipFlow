"""Pydantic models for project folders."""

from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


class Folder(BaseModel):
    """A project folder containing videos and an optional style profile."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    video_ids: list[str] = Field(default_factory=list)
    style_id: str | None = None


class FolderCreate(BaseModel):
    """Request body for creating a folder."""

    name: str
    style_id: str | None = None


class FolderUpdate(BaseModel):
    """Request body for updating a folder."""

    name: str | None = None
    style_id: str | None = None


class FolderAddVideo(BaseModel):
    """Request body for adding a video to a folder."""

    video_id: str
