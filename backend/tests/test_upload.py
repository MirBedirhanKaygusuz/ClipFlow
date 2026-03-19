"""Tests for upload endpoint."""

import pytest
from io import BytesIO


@pytest.mark.asyncio
async def test_upload_valid_mp4(client):
    """Valid .mp4 upload returns file_id and size."""
    content = b"\x00" * 1024  # 1KB dummy
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("test.mp4", BytesIO(content), "video/mp4")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert "size_mb" in data


@pytest.mark.asyncio
async def test_upload_invalid_extension(client):
    """Non-video file returns 400."""
    content = b"not a video"
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("test.txt", BytesIO(content), "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_mov_accepted(client):
    """.mov files should be accepted."""
    content = b"\x00" * 512
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("video.mov", BytesIO(content), "video/quicktime")},
    )
    assert response.status_code == 200
    assert "file_id" in response.json()
