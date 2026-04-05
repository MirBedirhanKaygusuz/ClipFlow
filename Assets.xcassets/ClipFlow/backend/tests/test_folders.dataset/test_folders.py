"""Tests for folder CRUD endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_folder(client):
    """POST /folders creates a new folder."""
    response = await client.post(
        "/api/v1/folders",
        json={"name": "Test Folder"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Folder"
    assert "id" in data
    assert data["video_ids"] == []


@pytest.mark.asyncio
async def test_list_folders_empty(client):
    """GET /folders returns empty list initially."""
    response = await client.get("/api/v1/folders")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_folders_after_create(client):
    """GET /folders returns created folders."""
    await client.post("/api/v1/folders", json={"name": "Folder 1"})
    await client.post("/api/v1/folders", json={"name": "Folder 2"})

    response = await client.get("/api/v1/folders")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_get_folder_by_id(client):
    """GET /folders/{id} returns specific folder."""
    create_resp = await client.post(
        "/api/v1/folders", json={"name": "My Folder"}
    )
    folder_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/folders/{folder_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "My Folder"


@pytest.mark.asyncio
async def test_get_folder_not_found(client):
    """GET /folders/{id} returns 404 for non-existent."""
    response = await client.get("/api/v1/folders/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_folder(client):
    """PUT /folders/{id} updates folder name."""
    create_resp = await client.post(
        "/api/v1/folders", json={"name": "Old Name"}
    )
    folder_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/folders/{folder_id}",
        json={"name": "New Name"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_folder_not_found(client):
    """PUT /folders/{id} returns 404 for non-existent."""
    response = await client.put(
        "/api/v1/folders/nonexistent",
        json={"name": "Whatever"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_folder(client):
    """DELETE /folders/{id} removes the folder."""
    create_resp = await client.post(
        "/api/v1/folders", json={"name": "Delete Me"}
    )
    folder_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/folders/{folder_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify deleted
    get_resp = await client.get(f"/api/v1/folders/{folder_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_folder_not_found(client):
    """DELETE /folders/{id} returns 404."""
    response = await client.delete("/api/v1/folders/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_video_to_folder(client):
    """POST /folders/{id}/videos adds video_id to folder."""
    create_resp = await client.post(
        "/api/v1/folders", json={"name": "Video Folder"}
    )
    folder_id = create_resp.json()["id"]

    add_resp = await client.post(
        f"/api/v1/folders/{folder_id}/videos",
        json={"video_id": "video-abc-123"},
    )
    assert add_resp.status_code == 200
    assert "video-abc-123" in add_resp.json()["video_ids"]


@pytest.mark.asyncio
async def test_add_video_duplicate_ignored(client):
    """Adding the same video twice doesn't duplicate it."""
    create_resp = await client.post(
        "/api/v1/folders", json={"name": "Dup Test"}
    )
    folder_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/folders/{folder_id}/videos",
        json={"video_id": "vid-1"},
    )
    resp = await client.post(
        f"/api/v1/folders/{folder_id}/videos",
        json={"video_id": "vid-1"},
    )
    assert resp.status_code == 200
    assert resp.json()["video_ids"].count("vid-1") == 1


@pytest.mark.asyncio
async def test_add_video_folder_not_found(client):
    """POST /folders/{id}/videos returns 404 for non-existent folder."""
    response = await client.post(
        "/api/v1/folders/nonexistent/videos",
        json={"video_id": "vid-1"},
    )
    assert response.status_code == 404
