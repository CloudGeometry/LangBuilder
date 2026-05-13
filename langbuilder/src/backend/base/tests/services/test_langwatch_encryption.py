"""Tests for F2-T7: API Key Encryption (Fernet) in LangWatchService.

Covers all 10 test cases:
1. save_key() stores encrypted (not plaintext) value in DB
2. Round-trip: save_key() + get_stored_key() returns original key
3. get_stored_key() returns None when no key stored
4. InvalidToken caught, returns None (rotated SECRET_KEY)
5. get_key_status() returns has_key=False when no key stored
6. get_key_status() returns has_key=True with correct preview "****xyz"
7. save_key() calls invalidate_cache() after saving
8. No plaintext key appears in log output
9. Calling save_key() twice updates existing row (no duplicates)
10. Legacy plaintext key (is_encrypted=False) returned as-is
"""
from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from langflow.services.langwatch.service import LangWatchService

# ── Constants ─────────────────────────────────────────────────────────────────

ADMIN_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TEST_API_KEY = "lw_test_abc123xyz"
TEST_SECRET_KEY = "test-secret-key-for-fernet-derivation"  # noqa: S105

# Patch target: the get_settings_service function as imported in the service module
_PATCH_TARGET = "langflow.services.langwatch.service.get_settings_service"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_fernet(secret_key: str) -> Fernet:
    """Derive Fernet from a given secret key (mirrors _get_fernet logic)."""
    key = base64.urlsafe_b64encode(
        hashlib.sha256(secret_key.encode()).digest()
    )
    return Fernet(key)


def _make_mock_settings(secret_key: str = TEST_SECRET_KEY):
    """Build a mock settings_service that returns the given secret key."""
    mock_secret = MagicMock()
    mock_secret.get_secret_value.return_value = secret_key
    mock_auth = MagicMock()
    mock_auth.SECRET_KEY = mock_secret
    mock_svc = MagicMock()
    mock_svc.auth_settings = mock_auth
    return mock_svc


def _make_setting(
    key: str = "LANGWATCH_API_KEY",
    value: str = "",
    is_encrypted: bool = True,  # noqa: FBT001, FBT002
) -> MagicMock:
    """Create a mock GlobalSettings-like object."""
    from datetime import timezone

    setting = MagicMock()
    setting.key = key
    setting.value = value
    setting.is_encrypted = is_encrypted
    setting.updated_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    setting.updated_by = ADMIN_UUID
    return setting


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def service():
    """LangWatchService instance with mocked DB and Redis."""
    svc = LangWatchService.__new__(LangWatchService)
    svc._db_session = AsyncMock()
    svc._client = LangWatchService._create_httpx_client()
    svc.redis = AsyncMock()
    svc.redis.keys = AsyncMock(return_value=[])
    svc.redis.delete = AsyncMock()
    return svc


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_key_stores_encrypted_value(service):
    """save_key() writes encrypted (not plaintext) value to DB."""
    service._get_setting = AsyncMock(return_value=None)
    service._db_session.commit = AsyncMock()

    captured_settings = []

    def capture_add(obj):
        captured_settings.append(obj)

    service._db_session.add = capture_add

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        await service.save_key(TEST_API_KEY, ADMIN_UUID)

    assert len(captured_settings) == 1
    stored_value = captured_settings[0].value
    # The stored value must NOT be the plaintext key
    assert stored_value != TEST_API_KEY
    # The stored value must be decryptable to the original key
    f = _make_fernet(TEST_SECRET_KEY)
    decrypted = f.decrypt(stored_value.encode()).decode()
    assert decrypted == TEST_API_KEY
    # is_encrypted must be True
    assert captured_settings[0].is_encrypted is True


@pytest.mark.asyncio
async def test_save_and_retrieve_key_round_trip(service):
    """Key saved with save_key() can be retrieved with get_stored_key()."""
    stored: dict = {}

    def capture_add(obj):
        stored["setting"] = obj

    service._db_session.add = capture_add
    service._db_session.commit = AsyncMock()

    call_count = {"n": 0}

    async def mock_get_setting(_key: str):
        call_count["n"] += 1
        if call_count["n"] <= 1:
            return None
        return stored.get("setting")

    service._get_setting = mock_get_setting

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        await service.save_key(TEST_API_KEY, ADMIN_UUID)
        retrieved = await service.get_stored_key()

    assert retrieved == TEST_API_KEY


@pytest.mark.asyncio
async def test_get_stored_key_returns_none_when_no_key(service):
    """get_stored_key() returns None when no key is stored."""
    service._get_setting = AsyncMock(return_value=None)

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        result = await service.get_stored_key()

    assert result is None


@pytest.mark.asyncio
async def test_invalid_token_returns_none(service):
    """InvalidToken caught, returns None (simulate rotated SECRET_KEY)."""
    # Encrypt with a DIFFERENT key than what _get_fernet will use
    other_fernet = _make_fernet("different-secret-key-xyz")
    encrypted_with_other = other_fernet.encrypt(TEST_API_KEY.encode()).decode()

    setting = _make_setting(value=encrypted_with_other, is_encrypted=True)
    service._get_setting = AsyncMock(return_value=setting)

    # _get_fernet uses TEST_SECRET_KEY, which cannot decrypt the other-key ciphertext
    with patch(_PATCH_TARGET, return_value=_make_mock_settings(TEST_SECRET_KEY)):
        result = await service.get_stored_key()

    assert result is None


@pytest.mark.asyncio
async def test_key_status_no_key(service):
    """get_key_status() returns has_key=False when no key stored."""
    service._get_setting = AsyncMock(return_value=None)

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        status = await service.get_key_status()

    assert status.has_key is False
    assert status.key_preview is None


@pytest.mark.asyncio
async def test_key_status_with_key(service):
    """get_key_status() returns has_key=True with correct preview format '****xyz'."""
    f = _make_fernet(TEST_SECRET_KEY)
    encrypted = f.encrypt(TEST_API_KEY.encode()).decode()
    setting = _make_setting(value=encrypted, is_encrypted=True)
    service._get_setting = AsyncMock(return_value=setting)

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        status = await service.get_key_status()

    assert status.has_key is True
    assert status.key_preview == "****xyz"
    assert status.configured_at == setting.updated_at


@pytest.mark.asyncio
async def test_save_key_invalidates_cache(service):
    """Verify invalidate_cache() is called after save_key()."""
    service._get_setting = AsyncMock(return_value=None)
    service._db_session.add = MagicMock()
    service._db_session.commit = AsyncMock()
    service.invalidate_cache = AsyncMock()

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        await service.save_key(TEST_API_KEY, ADMIN_UUID)

    service.invalidate_cache.assert_called_once()


@pytest.mark.asyncio
async def test_plaintext_key_not_in_logs(service, caplog):
    """Verify no plaintext key appears in log output (use caplog)."""
    service._get_setting = AsyncMock(return_value=None)
    service._db_session.add = MagicMock()
    service._db_session.commit = AsyncMock()

    with (
        patch(_PATCH_TARGET, return_value=_make_mock_settings()),
        caplog.at_level(logging.DEBUG, logger="langflow.services.langwatch.service"),
    ):
        await service.save_key(TEST_API_KEY, ADMIN_UUID)

    for record in caplog.records:
        assert TEST_API_KEY not in record.getMessage()


@pytest.mark.asyncio
async def test_save_key_updates_existing(service):
    """Calling save_key() twice updates the existing row (no duplicates)."""
    existing_setting = _make_setting(value="old-encrypted-value", is_encrypted=True)
    service._get_setting = AsyncMock(return_value=existing_setting)
    service._db_session.add = MagicMock()
    service._db_session.commit = AsyncMock()

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        await service.save_key(TEST_API_KEY, ADMIN_UUID)

    # db.add should be called once (update, not insert)
    service._db_session.add.assert_called_once()
    # The updated_by should be the admin UUID
    assert existing_setting.updated_by == ADMIN_UUID
    # The value should have been updated (not still the old value)
    assert existing_setting.value != "old-encrypted-value"
    assert existing_setting.is_encrypted is True


@pytest.mark.asyncio
async def test_legacy_plaintext_key(service):
    """If is_encrypted=False, return value as-is (legacy support)."""
    plain_setting = _make_setting(value="lw_legacy_plain_key", is_encrypted=False)
    service._get_setting = AsyncMock(return_value=plain_setting)

    with patch(_PATCH_TARGET, return_value=_make_mock_settings()):
        result = await service.get_stored_key()

    assert result == "lw_legacy_plain_key"
