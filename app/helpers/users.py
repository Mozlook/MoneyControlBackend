from fastapi import HTTPException
from ..models import User, UserSettings


def require_user_settings(user: User) -> "UserSettings":
    if user.user_settings is None:
        raise HTTPException(status_code=500, detail="User settings missing")
    return user.user_settings
