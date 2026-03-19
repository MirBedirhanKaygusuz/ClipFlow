"""Tests for process endpoint."""

import pytest


@pytest.mark.asyncio
async def test_start_process(client):
    """POST /process with valid body returns job_id."""
    response = await client.post(
        "/api/v1/process",
        json={"clip_ids": ["fake-id"], "mode": "talking_reels"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "estimated_seconds" in data


@pytest.mark.asyncio
async def test_start_process_invalid_mode(client):
    """Unknown mode returns 400."""
    response = await client.post(
        "/api/v1/process",
        json={"clip_ids": ["fake-id"], "mode": "nonexistent"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_status_not_found(client):
    """Non-existent job returns 404."""
    response = await client.get("/api/v1/process/nonexistent-job-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_status_after_submit(client):
    """Job exists and has a valid status after creation."""
    # Create a job (background task runs immediately with fake file, so it will fail)
    resp = await client.post(
        "/api/v1/process",
        json={"clip_ids": ["fake-id"], "mode": "talking_reels"},
    )
    job_id = resp.json()["job_id"]

    # Check status — job should exist with a valid status
    status_resp = await client.get(f"/api/v1/process/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ("queued", "processing", "failed")
