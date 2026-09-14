import uuid
from datetime import datetime, timedelta, timezone
import pytest
from jose import jwt
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)


def test_password_strength_validation():
    # Valid passwords
    assert validate_password_strength("ValidPass123!") is True
    assert validate_password_strength("Str0ng#P@ssword") is True

    # Invalid passwords
    assert validate_password_strength("short1!") is False  # < 8 chars
    assert validate_password_strength("alllowercase123!") is False  # no uppercase
    assert validate_password_strength("ALLUPPERCASE123!") is False  # no lowercase
    assert validate_password_strength("NoNumbersHere!") is False  # no number
    assert validate_password_strength("NoSpecialChar123") is False  # no special char
    assert validate_password_strength("") is False


def test_password_hashing_and_verification():
    raw_password = "SecurePassword123@"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123@", hashed) is False


def test_jwt_token_lifecycle():
    user_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    token_version = 1

    access_token = create_access_token(user_id, identity_id, token_version)
    refresh_token = create_refresh_token(user_id, identity_id, token_version)

    decoded_access = decode_jwt_token(access_token)
    assert decoded_access["sub"] == str(user_id)
    assert decoded_access["identity_id"] == str(identity_id)
    assert decoded_access["token_version"] == 1
    assert decoded_access["type"] == "access"

    decoded_refresh = decode_jwt_token(refresh_token)
    assert decoded_refresh["sub"] == str(user_id)
    assert decoded_refresh["type"] == "refresh"


def test_expired_jwt_rejection():
    # Create an expired token manually
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    payload = {
        "sub": str(uuid.uuid4()),
        "identity_id": str(uuid.uuid4()),
        "token_version": 1,
        "type": "access",
        "exp": int(expired_time.timestamp()),
    }
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(Exception):
        decode_jwt_token(expired_token)
