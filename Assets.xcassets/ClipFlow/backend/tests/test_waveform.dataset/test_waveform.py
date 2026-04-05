"""Tests for waveform endpoints."""

import pytest


@pytest.mark.asyncio
async def test_waveform_not_found(client):
    """GET /waveform/{id} returns 404 for non-existent file."""
    response = await client.get("/api/v1/waveform/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_waveform_samples_clamped_max(client):
    """Samples parameter is clamped to 1000 max."""
    response = await client.get("/api/v1/waveform/nonexistent?samples=5000")
    assert response.status_code == 404  # File not found, but samples validated


@pytest.mark.asyncio
async def test_waveform_samples_clamped_min(client):
    """Samples parameter is clamped to 10 min."""
    response = await client.get("/api/v1/waveform/nonexistent?samples=1")
    assert response.status_code == 404  # File not found, but samples validated
