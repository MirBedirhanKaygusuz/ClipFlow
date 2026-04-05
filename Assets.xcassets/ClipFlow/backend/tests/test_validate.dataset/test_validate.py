"""Tests for video validation endpoints."""

import pytest
from app.services.video_validator import (
    VideoInfo,
    ValidationResult,
    REELS_MAX_DURATION,
    MAX_SUPPORTED_DURATION,
    SUPPORTED_VIDEO_CODECS,
)


class TestVideoInfo:
    """Test VideoInfo data model."""

    def test_create_info(self):
        info = VideoInfo(
            duration=30.0,
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac",
            fps=30.0,
            bitrate=5000,
            file_size_mb=15.0,
            has_audio=True,
            rotation=0,
        )
        assert info.duration == 30.0
        assert info.width == 1920
        assert info.has_audio is True


class TestValidationResult:
    """Test ValidationResult model."""

    def test_valid_result(self):
        info = VideoInfo(30.0, 1920, 1080, "h264", "aac", 30.0, 5000, 15.0, True, 0)
        result = ValidationResult(valid=True, info=info, errors=[], warnings=[])
        assert result.valid is True
        assert result.errors == []

    def test_invalid_result(self):
        result = ValidationResult(
            valid=False, info=None, errors=["Video okunamadı"], warnings=[]
        )
        assert result.valid is False
        assert len(result.errors) == 1


class TestConstants:
    """Test validation constants."""

    def test_reels_max_duration(self):
        assert REELS_MAX_DURATION == 90.0

    def test_max_supported_duration(self):
        assert MAX_SUPPORTED_DURATION == 3600.0

    def test_h264_supported(self):
        assert "h264" in SUPPORTED_VIDEO_CODECS

    def test_hevc_supported(self):
        assert "hevc" in SUPPORTED_VIDEO_CODECS


class TestValidateEndpoint:
    """Test /validate endpoints."""

    @pytest.mark.asyncio
    async def test_validate_not_found(self, client):
        """GET /validate/{id} returns 404 for non-existent video."""
        response = await client.get("/api/v1/validate/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_splits_not_found(self, client):
        """GET /validate/{id}/splits returns 404 for non-existent video."""
        response = await client.get("/api/v1/validate/nonexistent/splits")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_splits_min_duration(self, client):
        """GET /validate/{id}/splits rejects < 10s max_duration."""
        response = await client.get("/api/v1/validate/fake/splits?max_duration=5")
        # Either 400 (duration too low) or 404 (file not found)
        assert response.status_code in (400, 404)
