from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated

from ..schemas.auth import GoogleAuthRequest, TokenResponse
from ..deps import get_db
from ..handlers import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
def auth_google(
    body: GoogleAuthRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return auth.auth_google(body=body, db=db)
