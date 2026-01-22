from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated

from ..schemas.auth import GoogleAuthRequest, TokenResponse
from ..auth.google import verify_google_id_token, InvalidGoogleTokenError
from ..auth.jwt import create_access_token
from ..deps import get_db
from ..models import User, UserOauth, UserSettings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
def auth_google(
    body: GoogleAuthRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        payload = verify_google_id_token(body.id_token)

    except InvalidGoogleTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        )

    google_sub = payload.get("sub")
    if not isinstance(google_sub, str):
        raise HTTPException(status_code=400, detail="Google payload missing 'sub'")

    email = payload.get("email")
    if not isinstance(email, str):
        raise HTTPException(status_code=400, detail="Google payload missing 'sub'")

    display_name = payload.get("name") if isinstance(payload.get("name"), str) else None

    oauth = (
        db.query(UserOauth)
        .filter(
            UserOauth.provider == "google",
            UserOauth.provider_sub == google_sub,
        )
        .first()
    )

    if oauth:
        user = oauth.user
    else:
        user = User(email=email, display_name=display_name)
        db.add(user)
        db.flush()

        oauth = UserOauth(
            user_id=user.id,
            provider="google",
            provider_sub=google_sub,
        )
        db.add(oauth)

        settings = UserSettings(
            id=user.id,
            language="pl",
            currency="PLN",
            billing_day=10,
            timezone="Europe/Warsaw",
        )
        db.add(settings)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
