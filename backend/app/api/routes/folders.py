"""Folder CRUD endpoints."""

from fastapi import APIRouter

import structlog

from app.exceptions import ClipFlowError
from app.models.folder import (
    AddVideoRequest,
    CreateFolderRequest,
    Folder,
    RenameFolderRequest,
)

router = APIRouter()
log = structlog.get_logger()

folder_store: dict[str, Folder] = {}


class FolderNotFoundError(ClipFlowError):
    """Raised when the requested folder does not exist."""

    def __init__(self, folder_id: str) -> None:
        """Initialise with the missing folder ID.

        Args:
            folder_id: The folder ID that was not found.
        """
        super().__init__(f"Folder not found: {folder_id}", 404)


class VideoNotInFolderError(ClipFlowError):
    """Raised when the requested video is not in the folder."""

    def __init__(self, video_id: str, folder_id: str) -> None:
        """Initialise with the missing video / folder pair.

        Args:
            video_id: The video ID that was not found.
            folder_id: The folder that was searched.
        """
        super().__init__(
            f"Video {video_id} not found in folder {folder_id}", 404
        )


@router.post("/folders", response_model=Folder, status_code=201)
async def create_folder(body: CreateFolderRequest) -> Folder:
    """Create a new empty folder.

    Args:
        body: JSON body containing the desired folder name.

    Returns:
        The newly created Folder object.
    """
    folder = Folder(name=body.name)
    folder_store[folder.id] = folder
    log.info("folder_created", folder_id=folder.id, name=folder.name)
    return folder


@router.get("/folders", response_model=list[Folder])
async def list_folders() -> list[Folder]:
    """Return all folders ordered by creation time (newest first).

    Returns:
        List of Folder objects sorted descending by created_at.
    """
    folders = sorted(
        folder_store.values(), key=lambda f: f.created_at, reverse=True
    )
    return list(folders)


@router.get("/folders/{folder_id}", response_model=Folder)
async def get_folder(folder_id: str) -> Folder:
    """Fetch a single folder by ID.

    Args:
        folder_id: UUID of the folder to retrieve.

    Returns:
        The matching Folder object.

    Raises:
        FolderNotFoundError: If no folder with that ID exists.
    """
    if folder_id not in folder_store:
        raise FolderNotFoundError(folder_id)
    return folder_store[folder_id]


@router.patch("/folders/{folder_id}", response_model=Folder)
async def rename_folder(folder_id: str, body: RenameFolderRequest) -> Folder:
    """Rename an existing folder.

    Args:
        folder_id: UUID of the folder to rename.
        body: JSON body containing the new name.

    Returns:
        The updated Folder object.

    Raises:
        FolderNotFoundError: If no folder with that ID exists.
    """
    if folder_id not in folder_store:
        raise FolderNotFoundError(folder_id)
    folder = folder_store[folder_id]
    folder.name = body.name
    log.info("folder_renamed", folder_id=folder_id, new_name=body.name)
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(folder_id: str) -> None:
    """Delete a folder (does not delete the underlying video files).

    Args:
        folder_id: UUID of the folder to delete.

    Raises:
        FolderNotFoundError: If no folder with that ID exists.
    """
    if folder_id not in folder_store:
        raise FolderNotFoundError(folder_id)
    del folder_store[folder_id]
    log.info("folder_deleted", folder_id=folder_id)


@router.post("/folders/{folder_id}/videos", response_model=Folder)
async def add_video_to_folder(folder_id: str, body: AddVideoRequest) -> Folder:
    """Add a video file ID to a folder.

    Duplicate video IDs are silently ignored.

    Args:
        folder_id: UUID of the target folder.
        body: JSON body containing the video_id to add.

    Returns:
        The updated Folder object.

    Raises:
        FolderNotFoundError: If no folder with that ID exists.
    """
    if folder_id not in folder_store:
        raise FolderNotFoundError(folder_id)
    folder = folder_store[folder_id]
    if body.video_id not in folder.video_ids:
        folder.video_ids.append(body.video_id)
        log.info(
            "video_added_to_folder",
            folder_id=folder_id,
            video_id=body.video_id,
        )
    return folder


@router.delete("/folders/{folder_id}/videos/{video_id}", response_model=Folder)
async def remove_video_from_folder(folder_id: str, video_id: str) -> Folder:
    """Remove a video file ID from a folder.

    Args:
        folder_id: UUID of the target folder.
        video_id: file_id of the video to remove.

    Returns:
        The updated Folder object.

    Raises:
        FolderNotFoundError: If no folder with that ID exists.
        VideoNotInFolderError: If the video_id is not in the folder.
    """
    if folder_id not in folder_store:
        raise FolderNotFoundError(folder_id)
    folder = folder_store[folder_id]
    if video_id not in folder.video_ids:
        raise VideoNotInFolderError(video_id, folder_id)
    folder.video_ids.remove(video_id)
    log.info(
        "video_removed_from_folder",
        folder_id=folder_id,
        video_id=video_id,
    )
    return folder
