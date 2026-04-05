"""AI-driven zoom/crop analyzer — spatial motion detection and keyframe generation.

Analyzes video frames in a grid pattern to detect where motion is happening,
then generates smooth zoom keyframes that focus on the most interesting regions.
Supports beat-synced zoom for musical edit mode.
"""

import asyncio
import json
import math
import re
from dataclasses import dataclass, asdict

import structlog

from app.services.ffmpeg_runner import run_ffmpeg, run_ffprobe

log = structlog.get_logger()

# Grid layout for spatial analysis (3x3 = 9 regions)
GRID_COLS = 3
GRID_ROWS = 3


@dataclass
class ZoomKeyframe:
    """A single zoom keyframe at a specific time."""

    timestamp: float  # seconds
    zoom_level: float  # 1.0 = normal, 2.0 = 2x zoom
    center_x: float  # 0.0 - 1.0 (normalized horizontal position)
    center_y: float  # 0.0 - 1.0 (normalized vertical position)
    duration: float  # how long this keyframe holds (seconds)

    def to_dict(self) -> dict:
        return asdict(self)


async def analyze_zoom_keyframes(
    video_path: str,
    zoom_intensity: float = 0.5,
    min_zoom: float = 1.0,
    max_zoom: float = 2.0,
    analysis_fps: float = 2.0,
) -> list[ZoomKeyframe]:
    """Analyze video and generate zoom keyframes based on spatial motion.

    Splits each frame into a 3x3 grid, measures motion in each region,
    then generates keyframes that zoom toward the most active region.

    Args:
        video_path: Path to the video file.
        zoom_intensity: How aggressively to zoom (0.0 = subtle, 1.0 = maximum).
        min_zoom: Minimum zoom level (1.0 = no zoom).
        max_zoom: Maximum zoom level.
        analysis_fps: How many frames per second to analyze.

    Returns:
        List of ZoomKeyframe objects sorted by timestamp.
    """
    # Get video info
    duration, width, height = await _get_video_info(video_path)
    if duration <= 0 or width <= 0 or height <= 0:
        log.warning("zoom_analysis_skip", reason="invalid video info")
        return []

    # Analyze motion in each grid region
    grid_scores = await _analyze_grid_motion(
        video_path, width, height, analysis_fps
    )

    if not grid_scores:
        log.warning("zoom_analysis_empty", video_path=video_path)
        return []

    # Generate keyframes from grid scores
    keyframes = _generate_keyframes(
        grid_scores=grid_scores,
        duration=duration,
        zoom_intensity=zoom_intensity,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
    )

    # Smooth transitions between keyframes
    keyframes = _smooth_keyframes(keyframes)

    log.info("zoom_keyframes_generated", count=len(keyframes))
    return keyframes


async def generate_beat_synced_zoom(
    keyframes: list[ZoomKeyframe],
    beat_times: list[float],
    onset_times: list[float] | None = None,
) -> list[ZoomKeyframe]:
    """Snap zoom keyframes to beat positions for musical sync.

    On beat hits: zoom in (toward max).
    Between beats: ease back out (toward min).
    Onset times (percussive hits) get extra zoom emphasis.

    Args:
        keyframes: Existing zoom keyframes with spatial info.
        beat_times: List of beat timestamps.
        onset_times: Optional onset timestamps for extra emphasis.

    Returns:
        New list of beat-aligned ZoomKeyframe objects.
    """
    if not keyframes or not beat_times:
        return keyframes

    onset_set = set()
    if onset_times:
        for ot in onset_times:
            onset_set.add(round(ot, 2))

    # Build a lookup: for any time, find the nearest keyframe's spatial info
    def _nearest_spatial(t: float) -> tuple[float, float]:
        best = min(keyframes, key=lambda k: abs(k.timestamp - t))
        return best.center_x, best.center_y

    synced = []
    for i, bt in enumerate(beat_times):
        cx, cy = _nearest_spatial(bt)

        # Determine zoom level based on beat strength
        is_downbeat = i % 4 == 0
        is_onset = round(bt, 2) in onset_set

        if is_onset and is_downbeat:
            zoom = keyframes[0].zoom_level if keyframes else 1.5  # strong zoom
            zoom = min(zoom * 1.3, 2.0)
        elif is_downbeat:
            zoom = keyframes[0].zoom_level if keyframes else 1.3
            zoom = min(zoom * 1.1, 1.8)
        else:
            zoom = 1.0 + (keyframes[0].zoom_level - 1.0 if keyframes else 0.2) * 0.6

        # Duration until next beat
        if i + 1 < len(beat_times):
            dur = beat_times[i + 1] - bt
        else:
            dur = 0.5

        synced.append(ZoomKeyframe(
            timestamp=round(bt, 3),
            zoom_level=round(zoom, 3),
            center_x=round(cx, 3),
            center_y=round(cy, 3),
            duration=round(dur, 3),
        ))

    return synced


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_video_info(video_path: str) -> tuple[float, int, int]:
    """Get video duration, width, and height."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path,
    ]
    stdout = await run_ffprobe(cmd)
    data = json.loads(stdout)

    duration = float(data.get("format", {}).get("duration", 0))
    width = 0
    height = 0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            break

    return duration, width, height


async def _analyze_grid_motion(
    video_path: str,
    width: int,
    height: int,
    analysis_fps: float,
) -> list[dict]:
    """Analyze motion in a 3x3 grid using FFmpeg.

    Runs 9 parallel FFmpeg analyses, one per grid cell. Each measures
    scene_score (frame-to-frame change) within that region.

    Returns:
        List of dicts: {"timestamp": float, "grid": [[score, ...], ...]}
        where grid[row][col] is the motion score for that cell.
    """
    cell_w = width // GRID_COLS
    cell_h = height // GRID_ROWS

    # Launch all 9 grid analyses concurrently
    tasks = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            x = col * cell_w
            y = row * cell_h
            tasks.append(_analyze_cell(video_path, x, y, cell_w, cell_h, analysis_fps))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results into timestamped grid snapshots
    # Each result is a list of {timestamp, score} for one cell
    cell_data = []
    for r in results:
        if isinstance(r, Exception):
            log.warning("grid_cell_failed", error=str(r))
            cell_data.append([])
        else:
            cell_data.append(r)

    # Build unified timeline
    all_timestamps = set()
    for cd in cell_data:
        for entry in cd:
            # Quantize to analysis_fps resolution
            t = round(entry["timestamp"] * analysis_fps) / analysis_fps
            all_timestamps.add(round(t, 3))

    timestamps = sorted(all_timestamps)
    if not timestamps:
        return []

    # For each timestamp, build a grid of motion scores
    grid_snapshots = []
    for t in timestamps:
        grid = [[0.0] * GRID_COLS for _ in range(GRID_ROWS)]

        for idx, cd in enumerate(cell_data):
            row = idx // GRID_COLS
            col = idx % GRID_COLS

            # Find closest score to this timestamp
            best_score = 0.0
            best_dist = float("inf")
            for entry in cd:
                dist = abs(entry["timestamp"] - t)
                if dist < best_dist and dist < (1.0 / analysis_fps):
                    best_dist = dist
                    best_score = entry["score"]

            grid[row][col] = best_score

        grid_snapshots.append({"timestamp": t, "grid": grid})

    return grid_snapshots


async def _analyze_cell(
    video_path: str,
    x: int,
    y: int,
    w: int,
    h: int,
    fps: float,
) -> list[dict]:
    """Analyze motion within a single grid cell.

    Uses FFmpeg crop + scene detection on a specific region of the frame.

    Returns:
        List of {"timestamp": float, "score": float} dicts.
    """
    # fps filter to reduce analysis workload, then crop to cell, then scene detect
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", (
            f"fps={fps},"
            f"crop={w}:{h}:{x}:{y},"
            f"select='gte(scene,0)',metadata=print:file=-"
        ),
        "-an", "-f", "null", "-",
    ]

    try:
        _, stderr = await run_ffmpeg(cmd, retries=0, timeout=120)
    except Exception as e:
        log.warning("cell_analysis_failed", x=x, y=y, error=str(e))
        return []

    scores = []
    current_time = None

    for line in stderr.split("\n"):
        time_match = re.search(r"pts_time:([\d.]+)", line)
        if time_match:
            current_time = float(time_match.group(1))

        score_match = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if score_match and current_time is not None:
            scores.append({
                "timestamp": round(current_time, 3),
                "score": float(score_match.group(1)),
            })

    return scores


def _generate_keyframes(
    grid_scores: list[dict],
    duration: float,
    zoom_intensity: float,
    min_zoom: float,
    max_zoom: float,
) -> list[ZoomKeyframe]:
    """Convert grid motion scores into zoom keyframes.

    For each timestamp, finds the grid region with the highest motion
    and creates a keyframe that zooms toward that region.

    Args:
        grid_scores: List of {"timestamp", "grid"} dicts.
        duration: Total video duration.
        zoom_intensity: Scale factor for zoom (0-1).
        min_zoom: Minimum zoom.
        max_zoom: Maximum zoom.
    """
    zoom_range = max_zoom - min_zoom
    keyframes = []

    for i, snap in enumerate(grid_scores):
        grid = snap["grid"]
        timestamp = snap["timestamp"]

        # Find the cell with highest motion
        max_score = 0.0
        best_row, best_col = 1, 1  # default to center

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if grid[r][c] > max_score:
                    max_score = grid[r][c]
                    best_row = r
                    best_col = c

        # Convert grid position to normalized coordinates (0-1)
        # Center of the cell
        center_x = (best_col + 0.5) / GRID_COLS
        center_y = (best_row + 0.5) / GRID_ROWS

        # Zoom level proportional to motion intensity
        zoom = min_zoom + zoom_range * min(max_score * zoom_intensity * 3, 1.0)
        zoom = max(min_zoom, min(max_zoom, zoom))

        # Low-motion frames stay at center with minimal zoom
        if max_score < 0.02:
            center_x = 0.5
            center_y = 0.5
            zoom = min_zoom

        # Duration until next keyframe
        if i + 1 < len(grid_scores):
            dur = grid_scores[i + 1]["timestamp"] - timestamp
        else:
            dur = duration - timestamp

        keyframes.append(ZoomKeyframe(
            timestamp=round(timestamp, 3),
            zoom_level=round(zoom, 3),
            center_x=round(center_x, 3),
            center_y=round(center_y, 3),
            duration=round(max(dur, 0.1), 3),
        ))

    return keyframes


def _smooth_keyframes(keyframes: list[ZoomKeyframe]) -> list[ZoomKeyframe]:
    """Apply smoothing to prevent jarring zoom/pan jumps.

    Uses exponential moving average on zoom_level, center_x, center_y.
    """
    if len(keyframes) <= 1:
        return keyframes

    alpha = 0.4  # smoothing factor (lower = smoother, more latency)
    smoothed = [keyframes[0]]

    for i in range(1, len(keyframes)):
        prev = smoothed[-1]
        curr = keyframes[i]

        smoothed.append(ZoomKeyframe(
            timestamp=curr.timestamp,
            zoom_level=round(alpha * curr.zoom_level + (1 - alpha) * prev.zoom_level, 3),
            center_x=round(alpha * curr.center_x + (1 - alpha) * prev.center_x, 3),
            center_y=round(alpha * curr.center_y + (1 - alpha) * prev.center_y, 3),
            duration=curr.duration,
        ))

    return smoothed


def build_zoompan_filter(
    keyframes: list[ZoomKeyframe],
    input_width: int,
    input_height: int,
    output_width: int = 1080,
    output_height: int = 1920,
    fps: int = 30,
) -> str:
    """Build FFmpeg zoompan filter expression from keyframes.

    Generates a zoompan filter that smoothly animates between keyframes,
    outputting at the target resolution.

    Args:
        keyframes: Zoom keyframes to animate.
        input_width: Source video width.
        input_height: Source video height.
        output_width: Target output width.
        output_height: Target output height.
        fps: Output frame rate.

    Returns:
        FFmpeg filter string for use in -vf parameter.
    """
    if not keyframes:
        # Fallback: center crop with no zoom
        return (
            f"scale={output_width}:{output_height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2:black"
        )

    # Build if/between chain for zoom, x, y
    z_parts = []
    x_parts = []
    y_parts = []

    for i, kf in enumerate(keyframes):
        start_frame = int(kf.timestamp * fps)
        end_frame = int((kf.timestamp + kf.duration) * fps)

        z = kf.zoom_level
        # Calculate crop position from normalized center
        # In zoompan: x and y are pixel offsets of the top-left corner of the crop area
        # crop_w = iw/zoom, crop_h = ih/zoom
        # x = center_x * iw - crop_w/2 = center_x * iw - iw/(2*zoom)
        # Clamped to valid range by zoompan automatically
        cx_expr = f"{kf.center_x}*iw-iw/{2*z:.3f}"
        cy_expr = f"{kf.center_y}*ih-ih/{2*z:.3f}"

        cond = f"between(on,{start_frame},{end_frame})"
        z_parts.append(f"if({cond},{z:.3f}")
        x_parts.append(f"if({cond},{cx_expr}")
        y_parts.append(f"if({cond},{cy_expr}")

    # Build nested if expressions with default fallback
    def _nest(parts: list[str], default: str) -> str:
        expr = default
        for p in reversed(parts):
            expr = f"{p},{expr})"
        return expr

    z_expr = _nest(z_parts, "1")
    x_expr = _nest(x_parts, "iw/2-iw/2")
    y_expr = _nest(y_parts, "ih/2-ih/2")

    # zoompan filter with expressions
    # d=1 means each input frame produces 1 output frame (no frame duplication)
    return (
        f"zoompan=z='{z_expr}'"
        f":x='{x_expr}'"
        f":y='{y_expr}'"
        f":d=1"
        f":s={output_width}x{output_height}"
        f":fps={fps}"
    )
