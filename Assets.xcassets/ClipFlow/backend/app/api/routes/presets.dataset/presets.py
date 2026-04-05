"""Export preset endpoints — list and query encoding presets."""

from fastapi import APIRouter, HTTPException

from app.services.export_presets import list_presets, get_preset, get_ffmpeg_args

router = APIRouter()


@router.get("/presets")
async def get_all_presets():
    """List all available export presets.

    Returns presets for Instagram Reels, TikTok, YouTube Shorts, etc.
    """
    return {"presets": list_presets()}


@router.get("/presets/{preset_id}")
async def get_preset_by_id(preset_id: str):
    """Get a specific preset by ID.

    Args:
        preset_id: The preset identifier (e.g., "instagram_reels").

    Returns:
        The preset configuration.
    """
    preset = get_preset(preset_id)
    if not preset:
        raise HTTPException(404, f"Preset bulunamadı: {preset_id}")
    return preset.to_dict()


@router.get("/presets/{preset_id}/ffmpeg")
async def get_preset_ffmpeg_args(preset_id: str):
    """Get FFmpeg encoding arguments for a preset.

    Useful for debugging or custom processing.
    """
    preset = get_preset(preset_id)
    if not preset:
        raise HTTPException(404, f"Preset bulunamadı: {preset_id}")

    return {
        "preset_id": preset_id,
        "ffmpeg_args": get_ffmpeg_args(preset),
    }
