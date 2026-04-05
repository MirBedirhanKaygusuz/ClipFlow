"""Tests for style profile endpoints."""

import pytest
from pathlib import Path
from app.config import settings


@pytest.mark.asyncio
async def test_create_style(client):
    """POST /styles with valid profile returns saved profile."""
    profile = {
        "name": "test-style",
        "duration": 30.0,
        "scene_count": 5,
        "avg_scene_duration": 6.0,
        "cut_frequency": 0.17,
        "audio": {},
        "scenes": [],
    }
    response = await client.post("/api/v1/styles", json=profile)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-style"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_styles_empty(client):
    """GET /styles returns empty list initially."""
    response = await client.get("/api/v1/styles")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_styles_after_create(client):
    """GET /styles returns created profiles."""
    profile = {
        "name": "style-a",
        "duration": 10.0,
        "scene_count": 2,
        "avg_scene_duration": 5.0,
        "cut_frequency": 0.2,
        "audio": {},
        "scenes": [],
    }
    await client.post("/api/v1/styles", json=profile)
    response = await client.get("/api/v1/styles")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_style_by_id(client):
    """GET /styles/{id} returns the correct profile."""
    profile = {
        "name": "get-test",
        "duration": 20.0,
        "scene_count": 3,
        "avg_scene_duration": 6.7,
        "cut_frequency": 0.15,
        "audio": {},
        "scenes": [],
    }
    create_resp = await client.post("/api/v1/styles", json=profile)
    style_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/styles/{style_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "get-test"


@pytest.mark.asyncio
async def test_get_style_not_found(client):
    """GET /styles/{id} returns 404 for non-existent."""
    response = await client.get("/api/v1/styles/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_style(client):
    """DELETE /styles/{id} removes the profile."""
    profile = {
        "name": "delete-me",
        "duration": 5.0,
        "scene_count": 1,
        "avg_scene_duration": 5.0,
        "cut_frequency": 0.2,
        "audio": {},
        "scenes": [],
    }
    create_resp = await client.post("/api/v1/styles", json=profile)
    style_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/styles/{style_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify deleted
    get_resp = await client.get(f"/api/v1/styles/{style_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_style_not_found(client):
    """DELETE /styles/{id} returns 404 for non-existent."""
    response = await client.delete("/api/v1/styles/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_style_video_not_found(client):
    """POST /styles/analyze returns 404 when video doesn't exist."""
    response = await client.post(
        "/api/v1/styles/analyze",
        json={"name": "test", "video_file_id": "nonexistent"},
    )
    assert response.status_code == 404
