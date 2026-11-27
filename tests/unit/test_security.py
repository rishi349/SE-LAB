from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import Settings
from app.core.errors import AuthenticationFailed
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRET = "unit-test-secret-0123456789-abcdefghijklmnop"


def test_password_hash_and_verify():
    hashed = hash_password("s3cret-password", rounds=4)
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong-password", hashed)
    assert not verify_password("anything", None)


def test_password_over_72_bytes_is_rejected():
    with pytest.raises(ValueError):
        hash_password("é" * 40, rounds=4)  # 80 bytes in UTF-8
    assert not verify_password("x" * 100, hash_password("x" * 72, rounds=4))


def test_token_round_trip_and_one_hour_expiry():
    now = datetime.now(UTC)
    token = create_access_token("USR0000000001", "user", SECRET, now=now)
    claims = decode_access_token(token, SECRET)
    assert claims["sub"] == "USR0000000001"
    assert claims["role"] == "user"
    assert claims["exp"] - claims["iat"] == 3600


def test_expired_token_is_rejected():
    issued = datetime.now(UTC) - timedelta(hours=1, seconds=5)
    token = create_access_token("USR0000000001", "user", SECRET, now=issued)
    with pytest.raises(AuthenticationFailed):
        decode_access_token(token, SECRET)


def test_wrong_secret_and_unsigned_tokens_are_rejected():
    token = create_access_token("USR0000000001", "user", SECRET)
    with pytest.raises(AuthenticationFailed):
        decode_access_token(token, SECRET + "-other")
    unsigned = jwt.encode({"sub": "USR0000000001", "type": "access"}, key=None, algorithm="none")
    with pytest.raises(AuthenticationFailed):
        decode_access_token(unsigned, SECRET)


def test_settings_require_strong_secret(tmp_path):
    with pytest.raises(RuntimeError):
        Settings(database_path=str(tmp_path / "x.db"), jwt_secret="short")
