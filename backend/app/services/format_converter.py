"""Video format conversion — 9:16 vertical, etc."""

import subprocess


def convert_to_vertical(input_path: str, output_path: str) -> None:
    """Convert video to 9:16 vertical format (1080x1920)."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
        ),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
