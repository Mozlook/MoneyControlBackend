from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..handlers import auth
from ..schemas.auth import GoogleAuthRequest, TokenResponse

from ..logging_setup import setup_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = setup_logger()


@router.post("/google", response_model=TokenResponse)
def auth_google(
    body: GoogleAuthRequest,
    db: Annotated[Session, Depends(get_db)],
    request: Request,
):
    try:
        token = auth.auth_google(body=body, db=db)

        logger.info(
            "google oauth login success",
            extra={
                "event_type": "auth_oauth_google_login_success",
                "src_ip": request.client.host if request.client else None,
                "user_agent": (request.headers.get("user-agent") or "")[:256],
                "data": {
                    "provider": "google",
                },
            },
        )
        return token

    except HTTPException as exc:
        logger.warning(
            "google oauth login failed",
            extra={
                "event_type": "auth_oauth_google_login_failed",
                "src_ip": request.client.host if request.client else None,
                "user_agent": (request.headers.get("user-agent") or "")[:256],
                "status": exc.status_code,
                "data": {
                    "provider": "google",
                    "detail": str(exc.detail)[:200],
                },
            },
        )
        raise

    except Exception as exc:
        logger.error(
            "google oauth login error",
            extra={
                "event_type": "auth_oauth_google_login_failed",
                "error_type": type(exc).__name__,
                "src_ip": request.client.host if request.client else None,
                "user_agent": (request.headers.get("user-agent") or "")[:256],
                "data": {"provider": "google"},
            },
            exc_info=True,
        )
        raise
