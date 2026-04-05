"""Tests for export presets endpoints and service."""

import pytest
from app.services.export_presets import (
    PRESETS,
    get_preset,
    list_presets,
    get_ffmpeg_args,
)


class TestPresetService:
    """Test export presets service."""

    def test_presets_not_empty(self):
        assert len(PRESETS) > 0

    def test_instagram_reels_exists(self):
        preset = get_preset("instagram_reels")
        assert preset is not None
        assert preset.width == 1080
        assert preset.height == 1920
        assert preset.aspect_ratio == "9:16"

    def test_tiktok_exists(self):
        preset = get_preset("tiktok")
        assert preset is not None
        assert preset.max_duration == 180.0

    def test_youtube_shorts_exists(self):
        preset = get_preset("youtube_shorts")
        assert preset is not None
        assert preset.max_duration == 60.0

    def test_nonexistent_preset_returns_none(self):
        assert get_preset("nonexistent") is None

    def test_list_presets_returns_all(self):
        result = list_presets()
        assert len(result) == len(PRESETS)
        assert all("id" in p for p in result)

    def test_ffmpeg_args_reels(self):
        preset = get_preset("instagram_reels")
        args = get_ffmpeg_args(preset)
        assert "-c:v" in args
        assert "libx264" in args
        assert "-b:v" in args
        assert "8000k" in args

    def test_ffmpeg_args_archive(self):
        preset = get_preset("archive_hq")
        args = get_ffmpeg_args(preset)
        assert "slow" in args
        assert "20000k" in args

    def test_square_preset(self):
        preset = get_preset("square")
        assert preset.width == 1080
        assert preset.height == 1080
        assert preset.aspect_ratio == "1:1"

    def test_ffmpeg_args_square_has_crop(self):
        preset = get_preset("square")
        args = get_ffmpeg_args(preset)
        vf_idx = args.index("-vf")
        assert "crop" in args[vf_idx + 1]


class TestPresetEndpoints:
    """Test /presets endpoints."""

    @pytest.mark.asyncio
    async def test_list_presets(self, client):
        response = await client.get("/api/v1/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert len(data["presets"]) > 0

    @pytest.mark.asyncio
    async def test_get_preset(self, client):
        response = await client.get("/api/v1/presets/instagram_reels")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "instagram_reels"
        assert data["width"] == 1080

    @pytest.mark.asyncio
    async def test_get_preset_not_found(self, client):
        response = await client.get("/api/v1/presets/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_ffmpeg_args(self, client):
        response = await client.get("/api/v1/presets/tiktok/ffmpeg")
        assert response.status_code == 200
        data = response.json()
        assert "ffmpeg_args" in data
        assert len(data["ffmpeg_args"]) > 0
