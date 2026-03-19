"""Tests for download endpoint."""

import pytest
from pathlib import Path

from app.config import settings


@pytest.mark.asyncio
async def test_download_not_found(client):
    """Non-existent file returns 404."""
    response = await client.get("/api/v1/download/nonexistent-file")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_valid_file(client):
    """Existing file returns 200 with video content."""
    # Create a dummy file in storage
    file_id = "test-download-file"
    file_path = Path(settings.storage_path) / f"{file_id}.mp4"
    file_path.write_bytes(b"\x00" * 256)

    response = await client.get(f"/api/v1/download/{file_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert "attachment" in response.headers.get("content-disposition", "")
