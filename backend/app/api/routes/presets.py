"""Export presets endpoint — platform-specific encoding profiles."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ExportPreset(BaseModel):
    """Platform-specific export configuration."""

    id: str
    name: str
    platform: str
    width: int
    height: int
    fps: int
    video_bitrate_kbps: int
    audio_bitrate_kbps: int
    max_duration: float
    aspect_ratio: str
    codec: str
    preset: str
    description: str


PRESETS: dict[str, ExportPreset] = {
    "instagram_reels": ExportPreset(
        id="instagram_reels", name="Instagram Reels", platform="Instagram",
        width=1080, height=1920, fps=30, video_bitrate_kbps=8000,
        audio_bitrate_kbps=128, max_duration=90, aspect_ratio="9:16",
        codec="h264", preset="fast",
        description="Instagram Reels için optimize — 9:16 dikey format",
    ),
    "tiktok": ExportPreset(
        id="tiktok", name="TikTok", platform="TikTok",
        width=1080, height=1920, fps=30, video_bitrate_kbps=6000,
        audio_bitrate_kbps=128, max_duration=180, aspect_ratio="9:16",
        codec="h264", preset="fast",
        description="TikTok için optimize — 3 dakikaya kadar",
    ),
    "youtube_shorts": ExportPreset(
        id="youtube_shorts", name="YouTube Shorts", platform="YouTube",
        width=1080, height=1920, fps=30, video_bitrate_kbps=10000,
        audio_bitrate_kbps=192, max_duration=60, aspect_ratio="9:16",
        codec="h264", preset="fast",
        description="YouTube Shorts — yüksek bitrate, 60 saniye limit",
    ),
    "youtube_standard": ExportPreset(
        id="youtube_standard", name="YouTube Standard", platform="YouTube",
        width=1920, height=1080, fps=30, video_bitrate_kbps=12000,
        audio_bitrate_kbps=192, max_duration=0, aspect_ratio="16:9",
        codec="h264", preset="medium",
        description="YouTube standart yatay video — süre limiti yok",
    ),
    "twitter": ExportPreset(
        id="twitter", name="X / Twitter", platform="Twitter",
        width=1080, height=1920, fps=30, video_bitrate_kbps=5000,
        audio_bitrate_kbps=128, max_duration=140, aspect_ratio="9:16",
        codec="h264", preset="fast",
        description="X/Twitter için optimize — 2:20 limit",
    ),
    "square": ExportPreset(
        id="square", name="Kare Format", platform="Genel",
        width=1080, height=1080, fps=30, video_bitrate_kbps=6000,
        audio_bitrate_kbps=128, max_duration=0, aspect_ratio="1:1",
        codec="h264", preset="fast",
        description="Kare format — Instagram feed, Facebook",
    ),
}


@router.get("/presets")
async def list_presets() -> dict:
    """List all available export presets.

    Returns:
        Dict with presets list.
    """
    return {"presets": list(PRESETS.values())}


@router.get("/presets/{preset_id}", response_model=ExportPreset)
async def get_preset(preset_id: str) -> ExportPreset:
    """Get a specific export preset by ID.

    Args:
        preset_id: Preset identifier.

    Returns:
        ExportPreset details.
    """
    preset = PRESETS.get(preset_id)
    if not preset:
        raise HTTPException(404, f"Preset bulunamadı: {preset_id}")
    return preset
