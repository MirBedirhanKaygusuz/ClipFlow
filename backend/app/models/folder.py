"""Pydantic models for folder management."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Folder(BaseModel):
    """Represents a user-created folder containing video clips.

    Attributes:
        id: Unique folder identifier (UUID).
        name: Human-readable folder name.
        created_at: ISO-8601 timestamp of creation.
        video_ids: Ordered list of video file IDs in this folder.
        style_id: Optional reference to a learned editing style.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    video_ids: list[str] = Field(default_factory=list)
    style_id: str | None = None


class CreateFolderRequest(BaseModel):
    """Request body for creating a new folder.

    Attributes:
        name: Desired folder name (must be non-empty).
    """

    name: str = Field(..., min_length=1, max_length=255)


class RenameFolderRequest(BaseModel):
    """Request body for renaming an existing folder.

    Attributes:
        name: New folder name (must be non-empty).
    """

    name: str = Field(..., min_length=1, max_length=255)


class AddVideoRequest(BaseModel):
    """Request body for adding a video to a folder.

    Attributes:
        video_id: file_id of the uploaded video to add.
    """

    video_id: str = Field(..., min_length=1)
