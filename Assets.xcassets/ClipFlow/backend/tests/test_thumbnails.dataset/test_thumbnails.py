"""Tests for thumbnail endpoints."""

import pytest
from io import BytesIO


@pytest.mark.asyncio
async def test_create_thumbnail_video_not_found(client):
    """POST /thumbnails/{id} returns 404 for non-existent video."""
    response = await client.post("/api/v1/thumbnails/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_thumbnail_video_not_found(client):
    """GET /thumbnails/{id} returns 404 for non-existent video."""
    response = await client.get("/api/v1/thumbnails/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_strip_video_not_found(client):
    """POST /thumbnails/{id}/strip returns 404 for non-existent video."""
    response = await client.post("/api/v1/thumbnails/nonexistent/strip")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_strip_frame_not_found(client):
    """GET /thumbnails/{id}/strip/{i} returns 404 for non-existent."""
    response = await client.get("/api/v1/thumbnails/nonexistent/strip/0")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_returns_thumbnail_url(client):
    """Upload response now includes thumbnail_url field."""
    content = b"\x00" * 1024
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("test.mp4", BytesIO(content), "video/mp4")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "thumbnail_url" in data
