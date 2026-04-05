"""Export presets — platform-specific encoding profiles.

Defines encoding settings for different social media platforms,
including resolution, bitrate, codec, and frame rate targets.
"""

from dataclasses import dataclass, asdict


@dataclass
class ExportPreset:
    """Export encoding preset for a specific platform."""

    id: str
    name: str
    platform: str
    width: int
    height: int
    fps: int
    video_bitrate_kbps: int
    audio_bitrate_kbps: int
    max_duration: float  # seconds, 0 = unlimited
    aspect_ratio: str  # "9:16", "16:9", "1:1", etc.
    codec: str  # libx264, libx265
    preset: str  # ultrafast, fast, medium, slow
    description: str

    def to_dict(self) -> dict:
        return asdict(self)


# Pre-defined export presets for popular platforms
PRESETS: dict[str, ExportPreset] = {
    "instagram_reels": ExportPreset(
        id="instagram_reels",
        name="Instagram Reels",
        platform="instagram",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate_kbps=8000,
        audio_bitrate_kbps=128,
        max_duration=90.0,
        aspect_ratio="9:16",
        codec="libx264",
        preset="fast",
        description="Instagram Reels için optimize. 9:16, 1080p, 30fps.",
    ),
    "instagram_story": ExportPreset(
        id="instagram_story",
        name="Instagram Story",
        platform="instagram",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate_kbps=6000,
        audio_bitrate_kbps=128,
        max_duration=60.0,
        aspect_ratio="9:16",
        codec="libx264",
        preset="fast",
        description="Instagram Story için optimize. 9:16, 1080p, 60s maks.",
    ),
    "tiktok": ExportPreset(
        id="tiktok",
        name="TikTok",
        platform="tiktok",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate_kbps=6000,
        audio_bitrate_kbps=128,
        max_duration=180.0,
        aspect_ratio="9:16",
        codec="libx264",
        preset="fast",
        description="TikTok için optimize. 9:16, 1080p, 3dk maks.",
    ),
    "youtube_shorts": ExportPreset(
        id="youtube_shorts",
        name="YouTube Shorts",
        platform="youtube",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate_kbps=10000,
        audio_bitrate_kbps=192,
        max_duration=60.0,
        aspect_ratio="9:16",
        codec="libx264",
        preset="medium",
        description="YouTube Shorts için optimize. 9:16, 1080p, yüksek bitrate.",
    ),
    "youtube_standard": ExportPreset(
        id="youtube_standard",
        name="YouTube (16:9)",
        platform="youtube",
        width=1920,
        height=1080,
        fps=30,
        video_bitrate_kbps=12000,
        audio_bitrate_kbps=192,
        max_duration=0,
        aspect_ratio="16:9",
        codec="libx264",
        preset="medium",
        description="YouTube standart video. 16:9, 1080p, yüksek kalite.",
    ),
    "youtube_4k": ExportPreset(
        id="youtube_4k",
        name="YouTube 4K",
        platform="youtube",
        width=3840,
        height=2160,
        fps=30,
        video_bitrate_kbps=35000,
        audio_bitrate_kbps=256,
        max_duration=0,
        aspect_ratio="16:9",
        codec="libx264",
        preset="slow",
        description="YouTube 4K video. 16:9, 2160p, en yüksek kalite.",
    ),
    "twitter": ExportPreset(
        id="twitter",
        name="X (Twitter)",
        platform="twitter",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate_kbps=5000,
        audio_bitrate_kbps=128,
        max_duration=140.0,
        aspect_ratio="9:16",
        codec="libx264",
        preset="fast",
        description="X/Twitter için optimize. 9:16, 1080p.",
    ),
    "square": ExportPreset(
        id="square",
        name="Kare (1:1)",
        platform="generic",
        width=1080,
        height=1080,
        fps=30,
        video_bitrate_kbps=6000,
        audio_bitrate_kbps=128,
        max_duration=0,
        aspect_ratio="1:1",
        codec="libx264",
        preset="fast",
        description="Kare format. Instagram feed, LinkedIn için ideal.",
    ),
    "archive_hq": ExportPreset(
        id="archive_hq",
        name="Arşiv (Yüksek Kalite)",
        platform="generic",
        width=0,  # 0 = keep original
        height=0,
        fps=0,  # 0 = keep original
        video_bitrate_kbps=20000,
        audio_bitrate_kbps=256,
        max_duration=0,
        aspect_ratio="original",
        codec="libx264",
        preset="slow",
        description="Orijinal çözünürlük, yüksek bitrate. Arşiv amaçlı.",
    ),
}


def get_preset(preset_id: str) -> ExportPreset | None:
    """Get a preset by ID."""
    return PRESETS.get(preset_id)


def list_presets() -> list[dict]:
    """List all available presets."""
    return [p.to_dict() for p in PRESETS.values()]


def get_ffmpeg_args(preset: ExportPreset) -> list[str]:
    """Convert a preset to FFmpeg encoding arguments.

    Returns a list of FFmpeg arguments for video and audio encoding
    based on the preset's specifications.
    """
    args = []

    # Video encoding
    args.extend(["-c:v", preset.codec])
    args.extend(["-preset", preset.preset])
    args.extend(["-b:v", f"{preset.video_bitrate_kbps}k"])

    # Resolution (0 = keep original)
    if preset.width > 0 and preset.height > 0:
        if preset.aspect_ratio == "1:1":
            # Square: crop to center then scale
            args.extend([
                "-vf",
                f"crop=min(iw\\,ih):min(iw\\,ih),"
                f"scale={preset.width}:{preset.height}",
            ])
        elif preset.aspect_ratio == "9:16":
            args.extend([
                "-vf",
                f"scale={preset.width}:{preset.height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={preset.width}:{preset.height}:(ow-iw)/2:(oh-ih)/2:black",
            ])
        elif preset.aspect_ratio == "16:9":
            args.extend([
                "-vf",
                f"scale={preset.width}:{preset.height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={preset.width}:{preset.height}:(ow-iw)/2:(oh-ih)/2:black",
            ])

    # FPS (0 = keep original)
    if preset.fps > 0:
        args.extend(["-r", str(preset.fps)])

    # Audio encoding
    args.extend(["-c:a", "aac"])
    args.extend(["-b:a", f"{preset.audio_bitrate_kbps}k"])

    return args
