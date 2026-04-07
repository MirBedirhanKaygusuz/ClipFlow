"""APNs push notification service using HTTP/2 via httpx.

Sends notifications to Apple Push Notification service for job completion and
failure events.  If APNs credentials are not configured the service logs a
warning and silently skips sending — callers are never expected to guard
against unconfigured state.

JWT tokens are generated per-request using PyJWT and the ES256 algorithm
required by APNs token-based authentication (p8 key files).
"""

import time
from typing import Any

import httpx
import structlog

from app.config import settings
from app.exceptions import PushNotificationError

logger: structlog.BoundLogger = structlog.get_logger(__name__)

_APNS_HOST = "https://api.push.apple.com"
_APNS_BUNDLE_ID = "com.clipflow.app"
_JWT_LIFETIME_SECONDS = 3000  # Apple recommends refreshing before 60 min


def _apns_configured() -> bool:
    """Return True when all APNs credentials are present in settings.

    Returns:
        bool: True if apns_key_path, apns_key_id, and apns_team_id are all
            non-empty strings.
    """
    return bool(settings.apns_key_path and settings.apns_key_id and settings.apns_team_id)


def _build_jwt() -> str:
    """Build a signed ES256 JWT for APNs token-based authentication.

    Reads the private key from settings.apns_key_path, which must be a .p8
    file in PKCS#8 PEM format as provided by Apple.

    Returns:
        str: Encoded JWT string suitable for the ``Authorization`` header.

    Raises:
        PushNotificationError: If PyJWT is missing, the key file cannot be
            read, or signing fails.
    """
    try:
        import jwt  # PyJWT
    except ImportError as exc:
        raise PushNotificationError("*", "PyJWT is not installed — add it to requirements.txt") from exc

    try:
        with open(settings.apns_key_path, "r") as fh:
            private_key = fh.read()
    except OSError as exc:
        raise PushNotificationError("*", f"Cannot read APNs key file: {exc}") from exc

    now = int(time.time())
    payload = {
        "iss": settings.apns_team_id,
        "iat": now,
    }
    headers = {
        "alg": "ES256",
        "kid": settings.apns_key_id,
    }
    try:
        token: str = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        return token
    except Exception as exc:
        raise PushNotificationError("*", f"JWT signing failed: {exc}") from exc


class PushService:
    """Async service for sending APNs push notifications to ClipFlow iOS clients.

    Usage::

        push = PushService()
        await push.send_processing_complete(device_token, job_id, stats)
        await push.send_processing_failed(device_token, job_id, "FFmpeg error")

    When APNs credentials are absent both methods log a warning and return
    immediately without raising an exception.
    """

    async def _send(
        self,
        device_token: str,
        payload: dict[str, Any],
        apns_push_type: str = "alert",
    ) -> None:
        """Deliver a single notification payload to APNs.

        Opens a new HTTP/2 connection per call.  For high-volume usage consider
        keeping a shared httpx.AsyncClient with HTTP/2 enabled.

        Args:
            device_token: Hex device token string obtained from the iOS app.
            payload: APNs payload dict (must contain an ``"aps"`` key).
            apns_push_type: Value for the ``apns-push-type`` header.  Defaults
                to ``"alert"``.

        Raises:
            PushNotificationError: If APNs returns a non-2xx response or the
                HTTP request itself fails.
        """
        jwt_token = _build_jwt()
        url = f"{_APNS_HOST}/3/device/{device_token}"
        headers = {
            "authorization": f"bearer {jwt_token}",
            "apns-push-type": apns_push_type,
            "apns-topic": _APNS_BUNDLE_ID,
        }

        try:
            async with httpx.AsyncClient(http2=True, timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise PushNotificationError(device_token, f"HTTP request failed: {exc}") from exc

        if response.status_code not in (200, 201):
            body = response.text[:300]
            raise PushNotificationError(
                device_token,
                f"APNs returned {response.status_code}: {body}",
            )

        logger.info(
            "push.sent",
            device_token=device_token[:8],
            push_type=apns_push_type,
            status=response.status_code,
        )

    async def send_processing_complete(
        self,
        device_token: str,
        job_id: str,
        stats: dict[str, Any],
    ) -> None:
        """Notify the device that a video processing job finished successfully.

        The notification includes a summary of processing stats (e.g. duration,
        silence removed, segments cut) so the iOS app can display them inline
        without an extra API round-trip.

        Args:
            device_token: Hex device token for the target device.
            job_id: Identifier of the completed job.
            stats: Arbitrary stats dict produced by the processing pipeline
                (e.g. ``{"duration_s": 42, "segments_removed": 3}``).

        Raises:
            PushNotificationError: If APNs delivery fails.  Silently returns
                when APNs credentials are not configured.
        """
        if not _apns_configured():
            logger.warning("push.skipped", reason="APNs not configured", job_id=job_id)
            return

        payload: dict[str, Any] = {
            "aps": {
                "alert": {
                    "title": "Video hazır!",
                    "body": "Düzenleme tamamlandı. Videoyu görüntülemek için dokun.",
                },
                "sound": "default",
                "badge": 1,
            },
            "job_id": job_id,
            "stats": stats,
        }
        await self._send(device_token, payload, apns_push_type="alert")

    async def send_processing_failed(
        self,
        device_token: str,
        job_id: str,
        error_msg: str,
    ) -> None:
        """Notify the device that a video processing job failed.

        Args:
            device_token: Hex device token for the target device.
            job_id: Identifier of the failed job.
            error_msg: Human-readable description of the failure reason.  Will
                be truncated to 200 characters before being embedded in the
                notification body.

        Raises:
            PushNotificationError: If APNs delivery fails.  Silently returns
                when APNs credentials are not configured.
        """
        if not _apns_configured():
            logger.warning("push.skipped", reason="APNs not configured", job_id=job_id)
            return

        truncated_error = error_msg[:200]
        payload: dict[str, Any] = {
            "aps": {
                "alert": {
                    "title": "İşlem başarısız",
                    "body": f"Video düzenlenemedi: {truncated_error}",
                },
                "sound": "default",
                "badge": 1,
            },
            "job_id": job_id,
            "error": truncated_error,
        }
        await self._send(device_token, payload, apns_push_type="alert")
