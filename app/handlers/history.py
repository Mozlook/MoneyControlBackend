from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..helpers.wallets import ensure_wallet_member
from ..helpers.periods import last_n_period_ranges_utc
from ..models import Transaction, User
from ..schemas.aggregation import LastPeriodsHistoryRead, PeriodTotalRead


def history_last_periods(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    periods: int = 6,
) -> LastPeriodsHistoryRead:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    currency = membership.wallet.currency

    if not 2 <= periods <= 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="periods needs to be between 2 and 8",
        )

    settings = current_user.user_settings
    if settings is None:
        raise HTTPException(status_code=500, detail="User settings missing")

    ranges = last_n_period_ranges_utc(
        billing_day=settings.billing_day,
        timezone_name=settings.timezone,
        periods=periods,
    )

    result_periods: list[PeriodTotalRead] = []

    for pr in ranges:
        total = (
            db.query(func.coalesce(func.sum(Transaction.amount_base), 0))
            .filter(
                Transaction.wallet_id == wallet_id,
                Transaction.deleted_at.is_(None),
                Transaction.type == "expense",
                Transaction.occurred_at >= pr.period_start_utc,
                Transaction.occurred_at < pr.period_end_utc,
            )
            .scalar()
        )

        result_periods.append(
            PeriodTotalRead(
                period_start=pr.period_start_utc,
                period_end=pr.period_end_utc,
                total=total,
            )
        )

    return LastPeriodsHistoryRead(currency=currency, periods=result_periods)
