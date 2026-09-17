import hashlib
import hmac
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from app.core.config import settings


LEGACY_SCRYPT_PREFIX = "legacy_scrypt$"


def validate_password_strength(password: str) -> bool:
    if not password or len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\/`~]", password):
        return False
    return True


def _verify_legacy_scrypt(plain_password: str, stored_value: str) -> bool:
    try:
        prefix, salt_hex, expected_hash = stored_value.split("$", 2)
        if prefix != "legacy_scrypt":
            return False
        candidate = hashlib.scrypt(
            plain_password.encode("utf-8"),
            salt=salt_hex.encode("utf-8"),
            n=2**14,
            r=8,
            p=1,
            dklen=64,
        ).hex()
        return hmac.compare_digest(candidate, expected_hash)
    except (ValueError, TypeError):
        return False


try:
    import bcrypt

    def get_password_hash(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if hashed_password.startswith(LEGACY_SCRYPT_PREFIX):
            return _verify_legacy_scrypt(plain_password, hashed_password)
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

except ImportError:
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        def get_password_hash(password: str) -> str:
            return pwd_context.hash(password)

        def verify_password(plain_password: str, hashed_password: str) -> bool:
            if hashed_password.startswith(LEGACY_SCRYPT_PREFIX):
                return _verify_legacy_scrypt(plain_password, hashed_password)
            return pwd_context.verify(plain_password, hashed_password)
    except ImportError:
        import crypt

        def get_password_hash(password: str) -> str:
            salt = crypt.mksalt(crypt.METHOD_BLOWFISH)
            return crypt.crypt(password, salt)

        def verify_password(plain_password: str, hashed_password: str) -> bool:
            if hashed_password.startswith(LEGACY_SCRYPT_PREFIX):
                return _verify_legacy_scrypt(plain_password, hashed_password)
            return crypt.crypt(plain_password, hashed_password) == hashed_password


def create_access_token(
    user_id: uuid.UUID,
    identity_id: uuid.UUID,
    token_version: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "identity_id": str(identity_id),
        "token_version": token_version,
        "type": "access",
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    user_id: uuid.UUID,
    identity_id: uuid.UUID,
    token_version: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "identity_id": str(identity_id),
        "token_version": token_version,
        "type": "refresh",
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
