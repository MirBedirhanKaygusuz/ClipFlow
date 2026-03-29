"""Shared test fixtures."""

import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest.fixture
async def client():
    """Async HTTP test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def setup_storage(tmp_path: Path):
    """Use tmp_path as storage for all tests."""
    original = settings.storage_path
    settings.storage_path = str(tmp_path)
    yield
    settings.storage_path = original
