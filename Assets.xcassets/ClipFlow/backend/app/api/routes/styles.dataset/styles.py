"""Style profile endpoints — analyze, save, list, delete."""

from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.config import settings
from app.models.style_profile import (
    StyleProfile,
    StyleProfileCreate,
    AudioProfile,
)
from app.services.style_analyzer import analyze_style
from app.services.style_store import save_style, get_style, list_styles, delete_style

router = APIRouter()


@router.post("/styles/analyze", response_model=StyleProfile)
async def analyze_and_create_style(request: StyleProfileCreate):
    """Analyze a video and create a style profile from it.

    Args:
        request: Contains name and video_file_id to analyze.

    Returns:
        The created StyleProfile with analysis results.
    """
    video_path = Path(settings.storage_path) / f"{request.video_file_id}.mp4"
    if not video_path.exists():
        raise HTTPException(404, f"Video bulunamadı: {request.video_file_id}")

    analysis = await analyze_style(str(video_path))

    audio_data = analysis.get("audio", {})
    profile = StyleProfile(
        name=request.name,
        duration=analysis.get("duration", 0),
        scene_count=analysis.get("scene_count", 0),
        avg_scene_duration=analysis.get("avg_scene_duration", 0),
        cut_frequency=analysis.get("cut_frequency", 0),
        resolution=analysis.get("resolution"),
        fps=analysis.get("fps"),
        audio=AudioProfile(**audio_data) if audio_data else AudioProfile(),
        scenes=analysis.get("scenes", []),
    )

    saved = await save_style(profile)
    return saved


@router.post("/styles", response_model=StyleProfile)
async def create_style(profile: StyleProfile):
    """Save a manually created style profile.

    Args:
        profile: The complete style profile to save.

    Returns:
        The saved StyleProfile.
    """
    saved = await save_style(profile)
    return saved


@router.get("/styles", response_model=list[StyleProfile])
async def get_all_styles():
    """List all saved style profiles."""
    return await list_styles()


@router.get("/styles/{style_id}", response_model=StyleProfile)
async def get_style_by_id(style_id: str):
    """Get a specific style profile by ID.

    Args:
        style_id: The style profile ID.

    Raises:
        HTTPException: 404 if not found.
    """
    profile = await get_style(style_id)
    if not profile:
        raise HTTPException(404, f"Stil profili bulunamadı: {style_id}")
    return profile


@router.delete("/styles/{style_id}")
async def delete_style_by_id(style_id: str):
    """Delete a style profile by ID.

    Args:
        style_id: The style profile ID.

    Raises:
        HTTPException: 404 if not found.
    """
    deleted = await delete_style(style_id)
    if not deleted:
        raise HTTPException(404, f"Stil profili bulunamadı: {style_id}")
    return {"status": "deleted", "id": style_id}
