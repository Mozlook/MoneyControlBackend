import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from ..config import settings


class InvalidTokenError(Exception):
    """Raised when the access token is invalid or cannot be decoded."""

    pass


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)

    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise InvalidTokenError("Invalid or expired access token") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise InvalidTokenError("Token payload missing 'sub' claim")

    try:
        return uuid.UUID(sub)
    except ValueError as exc:
        raise InvalidTokenError("Invalid 'sub' UUID format") from exc
