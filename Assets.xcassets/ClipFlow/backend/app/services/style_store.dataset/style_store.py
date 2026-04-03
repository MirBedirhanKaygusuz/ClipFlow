"""Style profile storage — V1: JSON files on local disk."""

import json
import structlog
from pathlib import Path

from app.config import settings
from app.models.style_profile import StyleProfile

log = structlog.get_logger()


def _styles_dir() -> Path:
    """Get the styles storage directory, creating it if needed."""
    path = Path(settings.storage_path) / "styles"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_style(profile: StyleProfile) -> StyleProfile:
    """Save a style profile to disk.

    Args:
        profile: The style profile to save.

    Returns:
        The saved profile.
    """
    file_path = _styles_dir() / f"{profile.id}.json"
    file_path.write_text(profile.model_dump_json(indent=2))
    log.info("style_saved", id=profile.id, name=profile.name)
    return profile


async def get_style(style_id: str) -> StyleProfile | None:
    """Load a style profile by ID.

    Args:
        style_id: The style profile ID.

    Returns:
        The style profile, or None if not found.
    """
    file_path = _styles_dir() / f"{style_id}.json"
    if not file_path.exists():
        return None

    data = json.loads(file_path.read_text())
    return StyleProfile(**data)


async def list_styles() -> list[StyleProfile]:
    """List all saved style profiles.

    Returns:
        List of all style profiles, sorted by creation date (newest first).
    """
    styles = []
    for file_path in _styles_dir().glob("*.json"):
        try:
            data = json.loads(file_path.read_text())
            styles.append(StyleProfile(**data))
        except Exception as e:
            log.warning("style_load_error", file=str(file_path), error=str(e))

    styles.sort(key=lambda s: s.created_at, reverse=True)
    return styles


async def delete_style(style_id: str) -> bool:
    """Delete a style profile by ID.

    Args:
        style_id: The style profile ID to delete.

    Returns:
        True if deleted, False if not found.
    """
    file_path = _styles_dir() / f"{style_id}.json"
    if not file_path.exists():
        return False

    file_path.unlink()
    log.info("style_deleted", id=style_id)
    return True
