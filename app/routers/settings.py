from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.user_settings import UserSettingsRead, UserSettingsUpdate
from ..handlers import settings as settings_handler

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=UserSettingsRead)
def get_my_settings(
    current_user: CurrentUser,
):
    return settings_handler.get_my_settings(current_user=current_user)


@router.put("", response_model=UserSettingsRead)
def update_my_settings(
    body: UserSettingsUpdate,
    db: DB,
    current_user: CurrentUser,
):
    return settings_handler.update_my_settings(
        body=body, db=db, current_user=current_user
    )
