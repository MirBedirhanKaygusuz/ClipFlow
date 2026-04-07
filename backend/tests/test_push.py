"""Tests for the push notification service (app/services/push_notification.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEVICE_TOKEN = "a1b2c3d4" * 16  # 128-hex-char dummy APNs token
BUNDLE_ID = "com.clipflow.app"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def push_service():
    """Return a PushNotificationService with APNs credentials cleared."""
    from app.services.push_notification import PushNotificationService  # noqa: PLC0415
    return PushNotificationService()


@pytest.fixture()
def configured_push_service(tmp_path):
    """Return a PushNotificationService with fake-but-present APNs settings."""
    # Write a minimal dummy key file so path validation passes
    key_file = tmp_path / "AuthKey_TEST.p8"
    key_file.write_text("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n")

    original_key_path = settings.apns_key_path
    original_key_id = settings.apns_key_id
    original_team_id = settings.apns_team_id

    settings.apns_key_path = str(key_file)
    settings.apns_key_id = "TESTKEYID1"
    settings.apns_team_id = "TEAMID0001"

    from app.services.push_notification import PushNotificationService  # noqa: PLC0415
    svc = PushNotificationService()

    yield svc

    settings.apns_key_path = original_key_path
    settings.apns_key_id = original_key_id
    settings.apns_team_id = original_team_id


# ---------------------------------------------------------------------------
# Tests — graceful skip when APNs is not configured
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_skips_when_apns_not_configured(push_service):
    """send() returns None without raising when APNs credentials are absent."""
    # settings.apns_key_path == "" → service is unconfigured
    result = await push_service.send(
        device_token=DEVICE_TOKEN,
        title="Export ready",
        body="Your video is done!",
    )
    assert result is None


@pytest.mark.asyncio
async def test_send_does_not_raise_when_unconfigured(push_service):
    """No exception propagates when APNs is not configured."""
    try:
        await push_service.send(
            device_token=DEVICE_TOKEN,
            title="Done",
            body="All good",
        )
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"send() raised unexpectedly: {exc}")


@pytest.mark.asyncio
async def test_is_configured_false_when_credentials_missing(push_service):
    """is_configured property is False when APNs env vars are empty."""
    assert push_service.is_configured is False


# ---------------------------------------------------------------------------
# Tests — notification payload structure
# ---------------------------------------------------------------------------

def test_build_payload_contains_aps_key(push_service):
    """_build_payload returns a dict with an 'aps' top-level key."""
    payload = push_service._build_payload(
        title="Export done",
        body="Your video is ready to download.",
    )
    assert "aps" in payload


def test_build_payload_alert_has_title_and_body(push_service):
    """The aps.alert sub-dict contains the correct title and body."""
    payload = push_service._build_payload(
        title="Export done",
        body="Your video is ready.",
    )
    alert = payload["aps"]["alert"]
    assert alert["title"] == "Export done"
    assert alert["body"] == "Your video is ready."


def test_build_payload_includes_sound(push_service):
    """Default payload requests the default system sound."""
    payload = push_service._build_payload(title="T", body="B")
    assert payload["aps"].get("sound") == "default"


def test_build_payload_custom_data_passed_through(push_service):
    """Extra keyword arguments are included at the top level of the payload."""
    payload = push_service._build_payload(
        title="Done",
        body="Ready",
        job_id="job-xyz",
        file_id="file-abc",
    )
    assert payload.get("job_id") == "job-xyz"
    assert payload.get("file_id") == "file-abc"


def test_build_payload_badge_count(push_service):
    """badge kwarg is forwarded into aps.badge."""
    payload = push_service._build_payload(title="T", body="B", badge=3)
    assert payload["aps"].get("badge") == 3


# ---------------------------------------------------------------------------
# Tests — httpx APNs call (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_posts_to_apns_endpoint(configured_push_service):
    """When configured, send() makes a POST request to the APNs URL."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await configured_push_service.send(
            device_token=DEVICE_TOKEN,
            title="Export ready",
            body="Tap to download your clip.",
        )

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    url: str = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
    assert DEVICE_TOKEN in url


@pytest.mark.asyncio
async def test_send_includes_json_payload_in_request(configured_push_service):
    """The POST body sent to APNs contains the aps alert structure."""
    import json

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        await configured_push_service.send(
            device_token=DEVICE_TOKEN,
            title="Done",
            body="Video ready",
        )

    call_kwargs = mock_client.post.call_args.kwargs
    # Accept either 'content' (raw bytes) or 'json' kwarg
    raw = call_kwargs.get("content") or call_kwargs.get("data")
    if raw:
        body = json.loads(raw)
    else:
        body = call_kwargs.get("json", {})

    assert "aps" in body
    assert body["aps"]["alert"]["title"] == "Done"


@pytest.mark.asyncio
async def test_send_returns_none_on_apns_200(configured_push_service):
    """send() returns None (success, fire-and-forget) on HTTP 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await configured_push_service.send(
            device_token=DEVICE_TOKEN,
            title="Done",
            body="Ready",
        )

    assert result is None


@pytest.mark.asyncio
async def test_send_raises_on_apns_error_status(configured_push_service):
    """send() raises PushNotificationError when APNs returns a non-200 status."""
    from app.exceptions import PushNotificationError  # noqa: PLC0415

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"reason": "BadDeviceToken"}'

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(PushNotificationError):
            await configured_push_service.send(
                device_token=DEVICE_TOKEN,
                title="Done",
                body="Ready",
            )
