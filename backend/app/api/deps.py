import hmac
import uuid
from typing import AsyncGenerator, Tuple
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_jwt_token
from app.models.student import User, UserIdentity
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user_and_identity(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> Tuple[User, UserIdentity]:
    """
    Authenticates incoming requests by validating the JWT access token,
    and verifying that token_version strictly matches the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    revoked_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has been revoked or invalidated.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_jwt_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id_str = payload.get("sub")
        identity_id_str = payload.get("identity_id")
        token_version = payload.get("token_version")

        if not user_id_str or not identity_id_str or token_version is None:
            raise credentials_exception

        identity_id = uuid.UUID(identity_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user_repo = UserRepository(db)
    identity = await user_repo.get_identity_by_id(identity_id)

    if not identity or not identity.user.is_active:
        raise credentials_exception

    # Enforce token version matching against database
    if identity.token_version != token_version:
        raise revoked_token_exception

    return identity.user, identity


async def get_current_user(
    user_and_identity: Tuple[User, UserIdentity] = Depends(get_current_user_and_identity),
) -> User:
    user, _ = user_and_identity
    return user


async def verify_admin_secret(
    x_admin_secret: str = Header(..., description="Secret administrative key for internal operational telemetry"),
) -> bool:
    """
    Secures internal metrics from public scraping.
    """
    if not hmac.compare_digest(x_admin_secret, settings.ADMIN_METRICS_SECRET):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid administrative secret.",
        )
    return True
