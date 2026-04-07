"""Tests for the storage service (app/services/storage.py)."""

import pytest
from pathlib import Path

from app.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _storage_path() -> Path:
    """Return the current storage root as a Path object."""
    return Path(settings.storage_path)


# ---------------------------------------------------------------------------
# Import guard — the service will not exist yet when this file is first read,
# so we import lazily inside each test so the file can be collected cleanly.
# ---------------------------------------------------------------------------

@pytest.fixture()
def storage():
    """Return the StorageService instance under test."""
    from app.services.storage import StorageService  # noqa: PLC0415
    return StorageService()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_and_read_file(storage):
    """Saving bytes and reading them back returns identical content."""
    data = b"hello clipflow " * 64
    file_id = "unit-test-read"

    await storage.save(file_id, data, extension=".mp4")
    result = await storage.read(file_id, extension=".mp4")

    assert result == data


@pytest.mark.asyncio
async def test_file_exists_true_after_save(storage):
    """file_exists returns True once a file has been saved."""
    file_id = "unit-test-exists"

    await storage.save(file_id, b"\x00" * 128, extension=".mp4")

    assert await storage.file_exists(file_id, extension=".mp4") is True


@pytest.mark.asyncio
async def test_file_exists_false_for_missing(storage):
    """file_exists returns False when no file has been saved with that id."""
    assert await storage.file_exists("does-not-exist", extension=".mp4") is False


@pytest.mark.asyncio
async def test_delete_removes_file(storage):
    """delete removes the file so file_exists returns False afterwards."""
    file_id = "unit-test-delete"

    await storage.save(file_id, b"data", extension=".mp4")
    assert await storage.file_exists(file_id, extension=".mp4") is True

    await storage.delete(file_id, extension=".mp4")

    assert await storage.file_exists(file_id, extension=".mp4") is False


@pytest.mark.asyncio
async def test_delete_missing_file_does_not_raise(storage):
    """Deleting a non-existent file should not raise an exception."""
    # Should complete without error
    await storage.delete("ghost-file", extension=".mp4")


@pytest.mark.asyncio
async def test_save_overwrites_existing_file(storage):
    """A second save with the same id replaces the previous content."""
    file_id = "unit-test-overwrite"
    original = b"original content"
    updated = b"updated content"

    await storage.save(file_id, original, extension=".mp4")
    await storage.save(file_id, updated, extension=".mp4")
    result = await storage.read(file_id, extension=".mp4")

    assert result == updated


@pytest.mark.asyncio
async def test_saved_file_exists_on_disk(storage):
    """The file saved via StorageService is actually present on the filesystem."""
    file_id = "unit-test-disk"
    data = b"\xff\xd8\xff"  # fake JPEG magic — any bytes will do

    await storage.save(file_id, data, extension=".mp4")

    expected_path = _storage_path() / f"{file_id}.mp4"
    assert expected_path.exists()
    assert expected_path.read_bytes() == data
