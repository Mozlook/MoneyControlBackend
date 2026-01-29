from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from ..models import User, UserSettings


def get_user_settings_or_404(user: User) -> UserSettings:
    settings = user.user_settings
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not configured",
        )
    return settings


def validate_language(value: str) -> str:
    v = value.strip()
    if len(v) != 2 or not v.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong language format",
        )
    return v.lower()


def validate_currency(value: str) -> str:
    v = value.strip()
    if len(v) != 3 or not v.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong currency format",
        )
    return v.upper()


def validate_timezone(value: str) -> str:
    v = value.strip()
    try:
        _ = ZoneInfo(v)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong timezone format",
        )
    return v


def validate_billing_day(value: int) -> int:
    if not (1 <= value <= 28):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong billing_day format",
        )
    return value
