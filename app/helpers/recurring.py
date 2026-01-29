from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlmodel import col

from ..models import RecurringTransaction


def normalize_currency(code: str) -> str:
    return code.strip().upper()


def ensure_currency_matches_wallet(*, currency_base: str, wallet_currency: str) -> str:
    c = normalize_currency(currency_base)
    if c != wallet_currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency_base must equal wallet currency",
        )
    return c


def get_recurring_or_404(
    db: Session,
    *,
    wallet_id: UUID,
    recurring_id: UUID,
    require_active: bool | None = None,
) -> RecurringTransaction:
    rec = (
        db.query(RecurringTransaction)
        .filter(
            col(RecurringTransaction.wallet_id) == wallet_id,
            col(RecurringTransaction.id) == recurring_id,
        )
        .first()
    )

    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring not found",
        )

    if require_active is True and rec.active is False:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring not found",
        )

    return rec


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
