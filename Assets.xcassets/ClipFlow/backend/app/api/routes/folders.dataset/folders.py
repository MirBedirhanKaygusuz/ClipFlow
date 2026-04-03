"""Folder CRUD endpoints — organize videos into projects."""

import json
import structlog
from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.config import settings
from app.models.folder import Folder, FolderCreate, FolderUpdate, FolderAddVideo

router = APIRouter()
log = structlog.get_logger()


def _folders_dir() -> Path:
    """Get the folders storage directory."""
    path = Path(settings.storage_path) / "folders"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_folder(folder_id: str) -> Folder | None:
    """Load a folder from disk."""
    file_path = _folders_dir() / f"{folder_id}.json"
    if not file_path.exists():
        return None
    return Folder(**json.loads(file_path.read_text()))


def _save_folder(folder: Folder) -> None:
    """Save a folder to disk."""
    file_path = _folders_dir() / f"{folder.id}.json"
    file_path.write_text(folder.model_dump_json(indent=2))


@router.post("/folders", response_model=Folder)
async def create_folder(request: FolderCreate):
    """Create a new project folder.

    Args:
        request: Folder name and optional style_id.

    Returns:
        The created Folder.
    """
    folder = Folder(name=request.name, style_id=request.style_id)
    _save_folder(folder)
    log.info("folder_created", id=folder.id, name=folder.name)
    return folder


@router.get("/folders", response_model=list[Folder])
async def list_folders():
    """List all folders, sorted by creation date (newest first)."""
    folders = []
    for file_path in _folders_dir().glob("*.json"):
        try:
            data = json.loads(file_path.read_text())
            folders.append(Folder(**data))
        except Exception as e:
            log.warning("folder_load_error", file=str(file_path), error=str(e))

    folders.sort(key=lambda f: f.created_at, reverse=True)
    return folders


@router.get("/folders/{folder_id}", response_model=Folder)
async def get_folder(folder_id: str):
    """Get a specific folder by ID."""
    folder = _load_folder(folder_id)
    if not folder:
        raise HTTPException(404, f"Klasör bulunamadı: {folder_id}")
    return folder


@router.put("/folders/{folder_id}", response_model=Folder)
async def update_folder(folder_id: str, request: FolderUpdate):
    """Update a folder's name or style.

    Args:
        folder_id: Folder ID.
        request: Fields to update.
    """
    folder = _load_folder(folder_id)
    if not folder:
        raise HTTPException(404, f"Klasör bulunamadı: {folder_id}")

    if request.name is not None:
        folder.name = request.name
    if request.style_id is not None:
        folder.style_id = request.style_id

    _save_folder(folder)
    log.info("folder_updated", id=folder_id)
    return folder


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    """Delete a folder by ID."""
    file_path = _folders_dir() / f"{folder_id}.json"
    if not file_path.exists():
        raise HTTPException(404, f"Klasör bulunamadı: {folder_id}")

    file_path.unlink()
    log.info("folder_deleted", id=folder_id)
    return {"status": "deleted", "id": folder_id}


@router.post("/folders/{folder_id}/videos", response_model=Folder)
async def add_video_to_folder(folder_id: str, request: FolderAddVideo):
    """Add a video to a folder.

    Args:
        folder_id: Folder ID.
        request: Contains video_id to add.
    """
    folder = _load_folder(folder_id)
    if not folder:
        raise HTTPException(404, f"Klasör bulunamadı: {folder_id}")

    if request.video_id not in folder.video_ids:
        folder.video_ids.append(request.video_id)
        _save_folder(folder)
        log.info("video_added_to_folder", folder_id=folder_id, video_id=request.video_id)

    return folder
