"""Tests for zoom analyzer service and zoom-enabled processing."""

import pytest
from app.services.zoom_analyzer import (
    ZoomKeyframe,
    _generate_keyframes,
    _smooth_keyframes,
    build_zoompan_filter,
    generate_beat_synced_zoom,
)


class TestZoomKeyframe:
    """Test ZoomKeyframe data model."""

    def test_create_keyframe(self):
        """ZoomKeyframe can be created with all fields."""
        kf = ZoomKeyframe(
            timestamp=1.0,
            zoom_level=1.5,
            center_x=0.5,
            center_y=0.5,
            duration=0.5,
        )
        assert kf.timestamp == 1.0
        assert kf.zoom_level == 1.5
        assert kf.center_x == 0.5
        assert kf.center_y == 0.5
        assert kf.duration == 0.5

    def test_to_dict(self):
        """ZoomKeyframe.to_dict returns correct dict."""
        kf = ZoomKeyframe(1.0, 1.5, 0.3, 0.7, 2.0)
        d = kf.to_dict()
        assert d["timestamp"] == 1.0
        assert d["zoom_level"] == 1.5
        assert d["center_x"] == 0.3
        assert d["center_y"] == 0.7
        assert d["duration"] == 2.0


class TestGenerateKeyframes:
    """Test keyframe generation from grid motion scores."""

    def test_empty_grid_scores(self):
        """Empty grid scores returns empty keyframes."""
        result = _generate_keyframes([], 10.0, 0.5, 1.0, 2.0)
        assert result == []

    def test_low_motion_stays_center(self):
        """Low motion frames should stay centered with minimal zoom."""
        grid_scores = [
            {
                "timestamp": 0.0,
                "grid": [[0.001, 0.001, 0.001],
                          [0.001, 0.001, 0.001],
                          [0.001, 0.001, 0.001]],
            },
        ]
        keyframes = _generate_keyframes(grid_scores, 5.0, 0.5, 1.0, 2.0)
        assert len(keyframes) == 1
        assert keyframes[0].center_x == 0.5
        assert keyframes[0].center_y == 0.5
        assert keyframes[0].zoom_level == 1.0

    def test_top_left_motion_shifts_focus(self):
        """High motion in top-left grid cell shifts center to top-left."""
        grid_scores = [
            {
                "timestamp": 0.0,
                "grid": [[0.8, 0.0, 0.0],
                          [0.0, 0.0, 0.0],
                          [0.0, 0.0, 0.0]],
            },
        ]
        keyframes = _generate_keyframes(grid_scores, 5.0, 0.5, 1.0, 2.0)
        assert len(keyframes) == 1
        # Top-left cell center: (0.5/3, 0.5/3) ≈ (0.167, 0.167)
        assert keyframes[0].center_x < 0.25
        assert keyframes[0].center_y < 0.25
        assert keyframes[0].zoom_level > 1.0

    def test_center_motion_stays_center(self):
        """High motion in center grid cell keeps center position."""
        grid_scores = [
            {
                "timestamp": 0.0,
                "grid": [[0.0, 0.0, 0.0],
                          [0.0, 0.9, 0.0],
                          [0.0, 0.0, 0.0]],
            },
        ]
        keyframes = _generate_keyframes(grid_scores, 5.0, 0.5, 1.0, 2.0)
        assert len(keyframes) == 1
        assert 0.4 <= keyframes[0].center_x <= 0.6
        assert 0.4 <= keyframes[0].center_y <= 0.6
        assert keyframes[0].zoom_level > 1.0

    def test_zoom_intensity_affects_zoom_level(self):
        """Higher zoom_intensity produces higher zoom levels."""
        grid_scores = [
            {
                "timestamp": 0.0,
                "grid": [[0.0, 0.0, 0.0],
                          [0.0, 0.5, 0.0],
                          [0.0, 0.0, 0.0]],
            },
        ]
        kf_low = _generate_keyframes(grid_scores, 5.0, 0.2, 1.0, 2.0)
        kf_high = _generate_keyframes(grid_scores, 5.0, 1.0, 1.0, 2.0)
        assert kf_high[0].zoom_level >= kf_low[0].zoom_level

    def test_zoom_clamped_to_max(self):
        """Zoom level never exceeds max_zoom."""
        grid_scores = [
            {
                "timestamp": 0.0,
                "grid": [[0.0, 0.0, 0.0],
                          [0.0, 1.0, 0.0],
                          [0.0, 0.0, 0.0]],
            },
        ]
        keyframes = _generate_keyframes(grid_scores, 5.0, 1.0, 1.0, 1.5)
        assert keyframes[0].zoom_level <= 1.5

    def test_multiple_timestamps(self):
        """Multiple grid snapshots produce multiple keyframes."""
        grid_scores = [
            {"timestamp": 0.0, "grid": [[0.5, 0, 0], [0, 0, 0], [0, 0, 0]]},
            {"timestamp": 1.0, "grid": [[0, 0, 0.5], [0, 0, 0], [0, 0, 0]]},
            {"timestamp": 2.0, "grid": [[0, 0, 0], [0, 0, 0], [0.5, 0, 0]]},
        ]
        keyframes = _generate_keyframes(grid_scores, 5.0, 0.5, 1.0, 2.0)
        assert len(keyframes) == 3


class TestSmoothKeyframes:
    """Test keyframe smoothing."""

    def test_single_keyframe_unchanged(self):
        """Single keyframe is returned as-is."""
        kf = [ZoomKeyframe(0.0, 1.5, 0.3, 0.7, 1.0)]
        result = _smooth_keyframes(kf)
        assert len(result) == 1
        assert result[0].zoom_level == 1.5

    def test_smoothing_reduces_jumps(self):
        """Smoothing reduces large differences between consecutive keyframes."""
        kfs = [
            ZoomKeyframe(0.0, 1.0, 0.5, 0.5, 0.5),
            ZoomKeyframe(0.5, 2.0, 0.1, 0.1, 0.5),
        ]
        smoothed = _smooth_keyframes(kfs)
        # Second keyframe should be between 1.0 and 2.0 (smoothed)
        assert 1.0 < smoothed[1].zoom_level < 2.0

    def test_empty_returns_empty(self):
        """Empty list returns empty list."""
        assert _smooth_keyframes([]) == []


class TestBuildZoompanFilter:
    """Test FFmpeg filter expression builder."""

    def test_empty_keyframes_fallback(self):
        """No keyframes returns center crop fallback."""
        result = build_zoompan_filter([], 1920, 1080)
        assert "pad=" in result
        assert "1080" in result
        assert "1920" in result

    def test_with_keyframes_produces_zoompan(self):
        """Keyframes produce a zoompan filter string."""
        kfs = [ZoomKeyframe(0.0, 1.5, 0.5, 0.5, 2.0)]
        result = build_zoompan_filter(kfs, 1920, 1080)
        assert "zoompan" in result
        assert "1080x1920" in result

    def test_filter_contains_zoom_expression(self):
        """Filter contains the zoom level from keyframe."""
        kfs = [ZoomKeyframe(0.0, 1.8, 0.3, 0.7, 1.0)]
        result = build_zoompan_filter(kfs, 1920, 1080, fps=30)
        assert "1.800" in result

    def test_multiple_keyframes_nested_if(self):
        """Multiple keyframes produce nested if/between expressions."""
        kfs = [
            ZoomKeyframe(0.0, 1.2, 0.5, 0.5, 1.0),
            ZoomKeyframe(1.0, 1.8, 0.3, 0.3, 1.0),
        ]
        result = build_zoompan_filter(kfs, 1920, 1080, fps=30)
        assert "between" in result
        # Should contain both zoom levels
        assert "1.200" in result
        assert "1.800" in result


class TestBeatSyncedZoom:
    """Test beat-synchronized zoom generation."""

    @pytest.mark.asyncio
    async def test_empty_beats_returns_original(self):
        """No beats returns original keyframes."""
        kfs = [ZoomKeyframe(0.0, 1.5, 0.5, 0.5, 1.0)]
        result = await generate_beat_synced_zoom(kfs, [])
        assert result == kfs

    @pytest.mark.asyncio
    async def test_empty_keyframes_returns_empty(self):
        """No keyframes returns empty."""
        result = await generate_beat_synced_zoom([], [0.5, 1.0, 1.5])
        assert result == []

    @pytest.mark.asyncio
    async def test_beat_count_matches(self):
        """Output has one keyframe per beat."""
        kfs = [ZoomKeyframe(0.0, 1.5, 0.5, 0.5, 5.0)]
        beats = [0.0, 0.5, 1.0, 1.5, 2.0]
        result = await generate_beat_synced_zoom(kfs, beats)
        assert len(result) == len(beats)

    @pytest.mark.asyncio
    async def test_downbeat_zoom_higher(self):
        """Downbeats (every 4th) get higher zoom than regular beats."""
        kfs = [ZoomKeyframe(0.0, 1.5, 0.5, 0.5, 5.0)]
        beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        result = await generate_beat_synced_zoom(kfs, beats)

        # Beat 0 (downbeat) and beat 4 (downbeat) should zoom more
        downbeat_zooms = [result[i].zoom_level for i in [0, 4]]
        regular_zooms = [result[i].zoom_level for i in [1, 2, 3]]
        assert min(downbeat_zooms) >= min(regular_zooms)

    @pytest.mark.asyncio
    async def test_timestamps_match_beats(self):
        """Output timestamps align with input beat times."""
        kfs = [ZoomKeyframe(0.0, 1.5, 0.5, 0.5, 5.0)]
        beats = [0.0, 0.5, 1.0]
        result = await generate_beat_synced_zoom(kfs, beats)
        assert [r.timestamp for r in result] == [0.0, 0.5, 1.0]


class TestProcessEndpointZoom:
    """Test /process endpoint accepts zoom settings."""

    @pytest.mark.asyncio
    async def test_process_with_zoom_enabled(self, client):
        """POST /process with enable_zoom in settings is accepted."""
        response = await client.post(
            "/api/v1/process",
            json={
                "clip_ids": ["fake-id"],
                "mode": "talking_reels",
                "settings": {
                    "enable_zoom": True,
                    "zoom_intensity": 0.7,
                },
            },
        )
        assert response.status_code == 200
        assert "job_id" in response.json()

    @pytest.mark.asyncio
    async def test_process_without_zoom_default(self, client):
        """POST /process without zoom settings works (backwards compatible)."""
        response = await client.post(
            "/api/v1/process",
            json={
                "clip_ids": ["fake-id"],
                "mode": "talking_reels",
            },
        )
        assert response.status_code == 200
        assert "job_id" in response.json()
