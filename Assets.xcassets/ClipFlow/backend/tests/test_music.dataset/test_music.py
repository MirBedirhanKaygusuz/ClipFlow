"""Tests for music library endpoints."""

import pytest
from io import BytesIO


@pytest.mark.asyncio
async def test_upload_music_multipart(client):
    """POST /music/upload with multipart returns music_id."""
    content = b"\x00" * 2048
    response = await client.post(
        "/api/v1/music/upload",
        files={"file": ("song.mp3", BytesIO(content), "audio/mpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "size_mb" in data
    assert data["filename"] == "song.mp3"


@pytest.mark.asyncio
async def test_upload_music_invalid_extension(client):
    """Non-audio file returns 400."""
    content = b"not audio"
    response = await client.post(
        "/api/v1/music/upload",
        files={"file": ("doc.pdf", BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_music_empty(client):
    """GET /music returns empty list initially."""
    response = await client.get("/api/v1/music")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_music_after_upload(client):
    """GET /music returns uploaded tracks."""
    content = b"\x00" * 512
    await client.post(
        "/api/v1/music/upload",
        files={"file": ("track.mp3", BytesIO(content), "audio/mpeg")},
    )

    response = await client.get("/api/v1/music")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_delete_music(client):
    """DELETE /music/{id} removes the track."""
    content = b"\x00" * 512
    upload_resp = await client.post(
        "/api/v1/music/upload",
        files={"file": ("del.mp3", BytesIO(content), "audio/mpeg")},
    )
    music_id = upload_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/music/{music_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify deleted
    list_resp = await client.get("/api/v1/music")
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_music_not_found(client):
    """DELETE /music/{id} returns 404 for non-existent."""
    response = await client.delete("/api/v1/music/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_music_not_found(client):
    """POST /music/{id}/analyze returns 404 for non-existent file."""
    response = await client.post("/api/v1/music/nonexistent/analyze")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /health returns ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
