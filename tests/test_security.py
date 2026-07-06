"""Unit tests for app.core.security (password hashing + JWT tokens)."""
from datetime import datetime, timezone

import jwt
import pytest

from app.core import security


def test_get_password_hash_is_not_plaintext():
    hashed = security.get_password_hash("my-password")
    assert hashed != "my-password"
    assert hashed.startswith("$2")  # bcrypt hash prefix


def test_get_password_hash_is_salted():
    """Two hashes of the same password must differ (random salt)."""
    assert security.get_password_hash("same") != security.get_password_hash("same")


def test_verify_password_success():
    hashed = security.get_password_hash("correct-horse")
    assert security.verify_password("correct-horse", hashed) is True


def test_verify_password_failure():
    hashed = security.get_password_hash("correct-horse")
    assert security.verify_password("wrong-password", hashed) is False


def test_create_access_token_roundtrip():
    token = security.create_access_token({"sub": "42"})
    payload = jwt.decode(
        token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
    )
    assert payload["sub"] == "42"


def test_create_access_token_sets_future_expiry():
    token = security.create_access_token({"sub": "1"})
    payload = jwt.decode(
        token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
    )
    assert "exp" in payload
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


def test_create_access_token_does_not_mutate_input():
    data = {"sub": "1"}
    security.create_access_token(data)
    assert "exp" not in data


def test_decode_with_wrong_secret_raises():
    token = security.create_access_token({"sub": "1"})
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "wrong-secret", algorithms=[security.ALGORITHM])
