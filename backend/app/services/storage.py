"""Storage service — local filesystem fallback with optional Cloudflare R2/S3 backend.

If R2 credentials (r2_endpoint, r2_access_key, r2_secret_key) are present in
settings, every operation is delegated to the R2 bucket via boto3.  Otherwise
files are stored under settings.storage_path on the local filesystem.  The
public interface is identical in both cases so callers never need to care which
backend is active.
"""

import asyncio
import logging
from pathlib import Path

import structlog

from app.config import settings
from app.exceptions import StorageError

logger: structlog.BoundLogger = structlog.get_logger(__name__)


def _r2_configured() -> bool:
    """Return True when all three R2 credentials are non-empty strings.

    Returns:
        bool: True if R2 is fully configured, False otherwise.
    """
    return bool(settings.r2_endpoint and settings.r2_access_key and settings.r2_secret_key)


class StorageService:
    """Async file storage abstraction over local filesystem or Cloudflare R2.

    Instantiation is cheap — the boto3 client is only created when R2 is
    configured, and it is reused across all method calls.

    Example:
        storage = StorageService()
        path = await storage.save_file("abc123", "mp4", video_bytes)
        exists = await storage.file_exists("abc123", "mp4")
        await storage.delete_file("abc123", "mp4")
    """

    def __init__(self) -> None:
        """Initialise storage backend based on current settings."""
        self._use_r2: bool = _r2_configured()
        self._s3_client = None  # lazy-loaded on first R2 call

        if self._use_r2:
            logger.info("storage.backend", backend="r2", bucket=settings.r2_bucket)
        else:
            local_root = Path(settings.storage_path)
            local_root.mkdir(parents=True, exist_ok=True)
            logger.info("storage.backend", backend="local", path=str(local_root))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_s3_client(self):
        """Return (and lazily create) the boto3 S3 client for R2.

        Returns:
            botocore.client.S3: Configured boto3 S3 client.

        Raises:
            StorageError: If boto3 cannot be imported or client creation fails.
        """
        if self._s3_client is not None:
            return self._s3_client
        try:
            import boto3  # type: ignore[import-untyped]

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint,
                aws_access_key_id=settings.r2_access_key,
                aws_secret_access_key=settings.r2_secret_key,
            )
            return self._s3_client
        except Exception as exc:
            raise StorageError("client_init", str(exc)) from exc

    @staticmethod
    def _object_key(file_id: str, ext: str) -> str:
        """Build the R2 object key (or local filename) for a given file.

        Args:
            file_id: Unique identifier for the file (e.g. a UUID).
            ext: File extension without leading dot (e.g. ``"mp4"``).

        Returns:
            str: The object key string ``"<file_id>.<ext>"``.
        """
        return f"{file_id}.{ext}"

    def _local_path(self, file_id: str, ext: str) -> Path:
        """Return the absolute local Path for a given file.

        Args:
            file_id: Unique identifier for the file.
            ext: File extension without leading dot.

        Returns:
            Path: Absolute path inside settings.storage_path.
        """
        return Path(settings.storage_path) / self._object_key(file_id, ext)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save_file(self, file_id: str, ext: str, data: bytes) -> str:
        """Persist raw bytes and return the storage key / local path string.

        Writes are performed in a thread-pool executor so the event loop is
        never blocked by I/O.

        Args:
            file_id: Unique identifier that will become part of the filename.
            ext: File extension without leading dot (e.g. ``"mp4"``).
            data: Raw file bytes to store.

        Returns:
            str: The object key (R2) or absolute path (local) that can be
                passed back to :meth:`get_file_path`.

        Raises:
            StorageError: If the write operation fails for any reason.
        """
        key = self._object_key(file_id, ext)
        try:
            if self._use_r2:
                client = self._get_s3_client()
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: client.put_object(
                        Bucket=settings.r2_bucket,
                        Key=key,
                        Body=data,
                    ),
                )
                logger.info("storage.save", backend="r2", key=key, bytes=len(data))
                return key
            else:
                local = self._local_path(file_id, ext)
                await asyncio.get_running_loop().run_in_executor(
                    None, local.write_bytes, data
                )
                logger.info("storage.save", backend="local", path=str(local), bytes=len(data))
                return str(local)
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError("save_file", str(exc)) from exc

    async def get_file_path(self, file_id: str, ext: str) -> str:
        """Return the storage key or absolute local path for an existing file.

        For the local backend the file is expected to already exist on disk.
        For R2 the object key is returned directly (callers are responsible for
        generating a pre-signed URL or streaming the object themselves).

        Args:
            file_id: Unique identifier for the file.
            ext: File extension without leading dot.

        Returns:
            str: Object key (R2) or absolute filesystem path (local).

        Raises:
            StorageError: If the file does not exist (local backend only).
        """
        if self._use_r2:
            return self._object_key(file_id, ext)

        local = self._local_path(file_id, ext)
        if not local.exists():
            raise StorageError("get_file_path", f"File not found: {local}")
        return str(local)

    async def delete_file(self, file_id: str, ext: str) -> None:
        """Remove a stored file from the active backend.

        Silently succeeds if the file does not exist (idempotent).

        Args:
            file_id: Unique identifier for the file.
            ext: File extension without leading dot.

        Raises:
            StorageError: If the deletion fails for a reason other than the
                file not existing.
        """
        key = self._object_key(file_id, ext)
        try:
            if self._use_r2:
                client = self._get_s3_client()
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: client.delete_object(Bucket=settings.r2_bucket, Key=key),
                )
                logger.info("storage.delete", backend="r2", key=key)
            else:
                local = self._local_path(file_id, ext)
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: local.unlink(missing_ok=True),
                )
                logger.info("storage.delete", backend="local", path=str(local))
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError("delete_file", str(exc)) from exc

    async def file_exists(self, file_id: str, ext: str) -> bool:
        """Check whether a file is present in the active backend.

        Args:
            file_id: Unique identifier for the file.
            ext: File extension without leading dot.

        Returns:
            bool: True if the file exists, False otherwise.

        Raises:
            StorageError: If the existence check itself fails (e.g. network
                error when talking to R2).
        """
        try:
            if self._use_r2:
                client = self._get_s3_client()
                key = self._object_key(file_id, ext)

                def _head() -> bool:
                    try:
                        client.head_object(Bucket=settings.r2_bucket, Key=key)
                        return True
                    except client.exceptions.ClientError:
                        return False

                return await asyncio.get_running_loop().run_in_executor(None, _head)
            else:
                local = self._local_path(file_id, ext)
                return await asyncio.get_running_loop().run_in_executor(None, local.exists)
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError("file_exists", str(exc)) from exc
