"""Custom exceptions for ClipFlow."""


class ClipFlowError(Exception):
    """Base exception for ClipFlow."""

    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)


class VideoTooLargeError(ClipFlowError):
    def __init__(self, size_mb: float):
        super().__init__(f"Video too large: {size_mb:.0f}MB (max 500MB)", 413)


class InvalidFormatError(ClipFlowError):
    def __init__(self, filename: str):
        super().__init__(f"Unsupported format: {filename}", 400)


class FFmpegError(ClipFlowError):
    def __init__(self, stderr: str):
        super().__init__(f"FFmpeg error: {stderr[:200]}", 500)


class JobNotFoundError(ClipFlowError):
    def __init__(self, job_id: str):
        super().__init__(f"Job not found: {job_id}", 404)


class ProcessingTimeoutError(ClipFlowError):
    def __init__(self, job_id: str):
        super().__init__(f"Processing timeout: {job_id}", 504)


class StorageError(ClipFlowError):
    """Raised when a file storage operation fails (local FS or R2)."""

    def __init__(self, operation: str, detail: str):
        super().__init__(f"Storage error during {operation}: {detail}", 500)


class PushNotificationError(ClipFlowError):
    """Raised when an APNs push notification cannot be delivered."""

    def __init__(self, device_token: str, detail: str):
        super().__init__(
            f"Push notification failed for token {device_token[:8]}…: {detail}", 502
        )
