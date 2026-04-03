"""Storage abstraction layer. V1: local filesystem, V2: Cloudflare R2."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

import aiofiles
import structlog

from app.config import settings

log = structlog.get_logger()


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def save(self, key: str, data: bytes | BinaryIO) -> str:
        """Save data with the given key. Returns the key."""
        ...

    @abstractmethod
    async def save_from_path(self, key: str, source_path: str) -> str:
        """Save a file from a local path. Returns the key."""
        ...

    @abstractmethod
    async def get_path(self, key: str) -> Path:
        """Get a local file path for the given key.

        For local storage, returns the direct path.
        For R2, downloads to a temp location and returns that path.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the file with the given key."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a file with the given key exists."""
        ...


class LocalStorage(StorageBackend):
    """Local filesystem storage (V1)."""

    def __init__(self) -> None:
        self.base_path = Path(settings.storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, data: bytes | BinaryIO) -> str:
        file_path = self.base_path / key
        if isinstance(data, bytes):
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(data)
        else:
            async with aiofiles.open(file_path, "wb") as f:
                while chunk := data.read(1024 * 1024):
                    await f.write(chunk)
        return key

    async def save_from_path(self, key: str, source_path: str) -> str:
        import shutil
        dest = self.base_path / key
        shutil.copy2(source_path, str(dest))
        return key

    async def get_path(self, key: str) -> Path:
        return self.base_path / key

    async def delete(self, key: str) -> None:
        file_path = self.base_path / key
        file_path.unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()


class R2Storage(StorageBackend):
    """Cloudflare R2 storage via boto3 S3-compatible API (V2)."""

    def __init__(self) -> None:
        import boto3
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key,
            aws_secret_access_key=settings.r2_secret_key,
        )
        self.bucket = settings.r2_bucket
        # Local cache for downloaded files
        self.cache_path = Path(settings.storage_path) / "_r2_cache"
        self.cache_path.mkdir(parents=True, exist_ok=True)
        log.info("r2_storage_initialized", bucket=self.bucket)

    async def save(self, key: str, data: bytes | BinaryIO) -> str:
        import asyncio
        if isinstance(data, bytes):
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=data,
            )
        else:
            await asyncio.to_thread(
                self.client.upload_fileobj,
                data,
                self.bucket,
                key,
            )
        log.info("r2_uploaded", key=key)
        return key

    async def save_from_path(self, key: str, source_path: str) -> str:
        import asyncio
        await asyncio.to_thread(
            self.client.upload_file,
            source_path,
            self.bucket,
            key,
        )
        log.info("r2_uploaded", key=key, source=source_path)
        return key

    async def get_path(self, key: str) -> Path:
        import asyncio
        local_path = self.cache_path / key
        local_path.parent.mkdir(parents=True, exist_ok=True)

        if not local_path.exists():
            await asyncio.to_thread(
                self.client.download_file,
                self.bucket,
                key,
                str(local_path),
            )
            log.info("r2_downloaded", key=key)

        return local_path

    async def delete(self, key: str) -> None:
        import asyncio
        await asyncio.to_thread(
            self.client.delete_object,
            Bucket=self.bucket,
            Key=key,
        )
        # Also clean local cache
        cache_file = self.cache_path / key
        cache_file.unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        import asyncio
        try:
            await asyncio.to_thread(
                self.client.head_object,
                Bucket=self.bucket,
                Key=key,
            )
            return True
        except self.client.exceptions.ClientError:
            return False


def get_storage() -> StorageBackend:
    """Factory function to get the configured storage backend."""
    if settings.r2_endpoint:
        return R2Storage()
    return LocalStorage()
