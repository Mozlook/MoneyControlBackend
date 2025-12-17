from __future__ import annotations

from google.auth.transport import requests
from google.oauth2 import id_token

from ..config import settings


class InvalidGoogleTokenError(Exception):
    """Raised when Google id_token is invalid or cannot be verified."""

    pass


def verify_google_id_token(token: str) -> dict[str, object]:
    """Verify Google ID token and return its payload.

    Raises:
        RuntimeError: gdy GOOGLE_CLIENT_ID nie jest skonfigurowane.
        InvalidGoogleTokenError: gdy token jest nieprawidłowy lub wygasł.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

    try:
        raw_payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise InvalidGoogleTokenError("Invalid Google ID token") from exc

    payload: dict[str, object] = dict(raw_payload)

    return payload
