from sqlalchemy.orm import Session

from ..models import User
from ..schemas.user_settings import UserSettingsRead, UserSettingsUpdate
from ..helpers.user_settings import (
    get_user_settings_or_404,
    validate_language,
    validate_currency,
    validate_timezone,
    validate_billing_day,
)


def get_my_settings(*, current_user: User) -> UserSettingsRead:
    user_settings = get_user_settings_or_404(current_user)
    return UserSettingsRead.model_validate(user_settings)


def update_my_settings(
    *,
    body: UserSettingsUpdate,
    db: Session,
    current_user: User,
) -> UserSettingsRead:
    user_settings = get_user_settings_or_404(current_user)

    if body.language is not None:
        user_settings.language = validate_language(body.language)

    if body.currency is not None:
        user_settings.currency = validate_currency(body.currency)

    if body.timezone is not None:
        user_settings.timezone = validate_timezone(body.timezone)

    if body.billing_day is not None:
        user_settings.billing_day = validate_billing_day(body.billing_day)

    db.commit()
    db.refresh(user_settings)

    return UserSettingsRead.model_validate(user_settings)
