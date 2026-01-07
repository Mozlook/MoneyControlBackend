from typing import Annotated
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.user_settings import UserSettingsRead, UserSettingsUpdate

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)


@router.get("/users/me/settings", response_model=UserSettingsRead, status_code=200)
def get_my_settings(
    current_user: Annotated[User, Depends(get_current_user)],
):
    user_settings = current_user.user_settings

    if user_settings is None:
        raise HTTPException(status_code=404, detail="User settings not configured")

    return UserSettingsRead.model_validate(user_settings)


@router.put("/users/me/settings", response_model=UserSettingsRead, status_code=200)
def update_my_settings(
    body: UserSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    user_settings = current_user.user_settings

    if user_settings is None:
        raise HTTPException(status_code=404, detail="User settings not configured")

    if body.language is not None:
        val = body.language.strip()
        if len(val) == 2:
            user_settings.language = val.lower()
        else:
            raise HTTPException(status_code=400, detail="Wrong language format")

    if body.currency is not None:
        val = body.currency.strip()
        if len(val) == 3:
            user_settings.currency = val.upper()
        else:
            raise HTTPException(status_code=400, detail="Wrong currency format")

    if body.timezone is not None:
        try:
            _ = ZoneInfo(body.timezone)
        except Exception:
            raise HTTPException(status_code=400, detail="Wrong timezone format")
        user_settings.timezone = body.timezone

    if body.billing_day is not None:
        if 1 <= body.billing_day <= 28:
            user_settings.billing_day = body.billing_day
        else:
            raise HTTPException(status_code=400, detail="Wrong billing_day format")

    db.commit()
    db.refresh(user_settings)

    return UserSettingsRead.model_validate(user_settings)
