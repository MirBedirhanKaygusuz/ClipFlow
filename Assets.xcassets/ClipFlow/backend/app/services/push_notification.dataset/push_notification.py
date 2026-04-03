"""APNs push notification service."""

import time
import jwt
import httpx
import structlog

from app.config import settings

log = structlog.get_logger()

# APNs endpoints
APNS_PRODUCTION = "https://api.push.apple.com"
APNS_SANDBOX = "https://api.sandbox.push.apple.com"


def _load_apns_key() -> str | None:
    """Load the APNs private key from the configured file path."""
    if not settings.apns_key_path:
        return None
    try:
        with open(settings.apns_key_path) as f:
            return f.read()
    except FileNotFoundError:
        log.warning("apns_key_not_found", path=settings.apns_key_path)
        return None


def _create_apns_token(key: str) -> str:
    """Create a JWT token for APNs authentication.

    Args:
        key: The APNs private key (p8 format).

    Returns:
        Signed JWT token string.
    """
    headers = {
        "alg": "ES256",
        "kid": settings.apns_key_id,
    }
    payload = {
        "iss": settings.apns_team_id,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, key, algorithm="ES256", headers=headers)


async def send_push(
    device_token: str,
    title: str,
    body: str,
    data: dict | None = None,
    sandbox: bool = False,
) -> bool:
    """Send a push notification via APNs.

    No-ops gracefully if APNs is not configured.

    Args:
        device_token: The device's push notification token.
        title: Notification title.
        body: Notification body text.
        data: Optional custom data payload.
        sandbox: Use sandbox APNs endpoint if True.

    Returns:
        True if notification was sent successfully, False otherwise.
    """
    if not device_token:
        return False

    key = _load_apns_key()
    if not key:
        log.debug("apns_not_configured")
        return False

    token = _create_apns_token(key)
    base_url = APNS_SANDBOX if sandbox else APNS_PRODUCTION
    url = f"{base_url}/3/device/{device_token}"

    payload = {
        "aps": {
            "alert": {
                "title": title,
                "body": body,
            },
            "sound": "default",
        },
    }
    if data:
        payload["data"] = data

    headers = {
        "authorization": f"bearer {token}",
        "apns-topic": "com.clipflow.app",
        "apns-push-type": "alert",
    }

    try:
        async with httpx.AsyncClient(http2=True) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            log.info("apns_sent", device_token=device_token[:8] + "...")
            return True
        else:
            log.warning(
                "apns_failed",
                status=response.status_code,
                body=response.text[:200],
            )
            return False

    except Exception as e:
        log.error("apns_error", error=str(e))
        return False


async def notify_job_complete(
    device_token: str | None, job_id: str, stats: dict | None = None
) -> None:
    """Send push notification when a job completes.

    Args:
        device_token: Device token (no-op if None).
        job_id: The completed job ID.
        stats: Optional processing stats.
    """
    if not device_token:
        return

    silence_pct = ""
    if stats and "silence_removed_pct" in stats:
        silence_pct = f" (%{stats['silence_removed_pct']} sessizlik kaldırıldı)"

    await send_push(
        device_token=device_token,
        title="Video Hazır!",
        body=f"Videonuz başarıyla işlendi{silence_pct}.",
        data={"job_id": job_id, "action": "download"},
    )


async def notify_job_failed(
    device_token: str | None, job_id: str, error: str = ""
) -> None:
    """Send push notification when a job fails.

    Args:
        device_token: Device token (no-op if None).
        job_id: The failed job ID.
        error: Error description.
    """
    if not device_token:
        return

    await send_push(
        device_token=device_token,
        title="İşlem Başarısız",
        body="Video işlenirken bir hata oluştu. Lütfen tekrar deneyin.",
        data={"job_id": job_id, "action": "retry"},
    )
