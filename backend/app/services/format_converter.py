"""Video format conversion — quality-aware encoding."""

import subprocess

from app.models.job import QualityMode


def encode_reels(input_path: str, output_path: str) -> None:
    """Encode for Instagram Reels/Story — max quality within platform limits.

    Args:
        input_path: Source video file path.
        output_path: Destination file path.

    Output spec:
        1080x1920 (9:16), H.264 High Profile L4.0, 10Mbps,
        30fps, yuv420p, AAC 128kbps 48kHz stereo, MP4 faststart.
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        # Video filters: scale to 9:16 + pad + cap fps at 30
        "-vf", (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            "fps=30"
        ),
        # Video codec: H.264 High Profile, high bitrate
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level:v", "4.0",
        "-pix_fmt", "yuv420p",
        "-b:v", "10M",
        "-maxrate", "12M",
        "-bufsize", "20M",
        "-preset", "fast",
        # Audio codec: AAC stereo
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-ac", "2",
        # Container: faststart for instant playback
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def encode_high_quality(input_path: str, output_path: str) -> None:
    """Encode preserving original quality — visually lossless.

    Args:
        input_path: Source video file path.
        output_path: Destination file path.

    Output spec:
        Original resolution, original fps, H.264 CRF 17,
        yuv420p, AAC 320kbps 48kHz, MP4 faststart.
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        # Video codec: CRF 17 = visually lossless
        "-c:v", "libx264",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        # Audio codec: studio quality
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        # Container: faststart
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def encode_output(input_path: str, output_path: str, quality: QualityMode) -> None:
    """Route to the correct encoder based on quality mode.

    Args:
        input_path: Source video file path.
        output_path: Destination file path.
        quality: QualityMode.REELS or QualityMode.HIGH_QUALITY.
    """
    if quality == QualityMode.REELS:
        encode_reels(input_path, output_path)
    else:
        encode_high_quality(input_path, output_path)
