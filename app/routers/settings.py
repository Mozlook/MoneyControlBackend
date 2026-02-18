from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..logging_setup import setup_logger
from ..models import User
from ..schemas.user_settings import UserSettingsRead, UserSettingsUpdate
from ..handlers import settings as settings_handler

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)

logger = setup_logger()

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _get_updates(body: UserSettingsUpdate) -> dict[str, object]:
    updates = body.model_dump(exclude_unset=True)
    return {str(k): v for k, v in updates.items()}


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
    request: Request,
):
    updates = _get_updates(body)
    changed_fields = list(updates.keys())

    try:
        settings = settings_handler.update_my_settings(
            body=body, db=db, current_user=current_user
        )

    except HTTPException as exc:
        if exc.status_code == 403:
            logger.warning(
                "permission denied",
                extra={
                    "event_type": "permission_denied",
                    "user_id": str(current_user.id),
                    "src_ip": request.client.host if request.client else None,
                    "user_agent": (request.headers.get("user-agent") or "")[:256],
                    "status": exc.status_code,
                    "data": {
                        "action": "settings_update",
                        "changed_fields": changed_fields,
                        "updates": updates,
                    },
                },
            )
        raise

    logger.info(
        "settings updated",
        extra={
            "event_type": "audit_settings_updated",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "changed_fields": changed_fields,
                "updates": updates,
            },
        },
    )

    return settings
