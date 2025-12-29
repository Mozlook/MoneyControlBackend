from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..helpers.wallets import ensure_wallet_member
from ..models import Transaction, User
from ..schemas.aggregation import LastPeriodsHistoryRead, PeriodTotalRead

router = APIRouter(
    prefix="/wallets/{wallet_id}/history",
    tags=["history"],
)


@router.get(
    "/last-periods",
    response_model=LastPeriodsHistoryRead,
    status_code=200,
)
def history_last_periods(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    periods: int = 6,
):
    membership = ensure_wallet_member(db, wallet_id, current_user)
    currency = membership.wallet.currency

    if not 2 <= periods <= 8:
        raise HTTPException(
            status_code=400, detail="periods needs to be between 2 and 8"
        )
    settings = current_user.user_settings
    local_tz = ZoneInfo(settings.timezone)
    now_utc = datetime.now(timezone.utc)

    now_local = now_utc.astimezone(local_tz)
    year = now_local.year
    month = now_local.month
    billing_day = settings.billing_day

    if now_local.day >= billing_day:
        period_start_local = datetime(year, month, billing_day, tzinfo=local_tz)
        if month == 12:
            period_end_local = datetime(year + 1, 1, billing_day, tzinfo=local_tz)
        else:
            period_end_local = datetime(year, month + 1, billing_day, tzinfo=local_tz)
    else:
        period_end_local = datetime(year, month, billing_day, tzinfo=local_tz)
        if month == 1:
            period_start_local = datetime(year - 1, 12, billing_day, tzinfo=local_tz)
        else:
            period_start_local = datetime(year, month - 1, billing_day, tzinfo=local_tz)

    result_periods: list[PeriodTotalRead] = []

    start_local = period_start_local
    end_local = period_end_local

    for _ in range(periods):
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)

        total = (
            db.query(func.coalesce(func.sum(Transaction.amount_base), 0))
            .filter(
                Transaction.wallet_id == wallet_id,
                Transaction.deleted_at.is_(None),
                Transaction.type == "expense",
                Transaction.occurred_at >= start_utc,
                Transaction.occurred_at < end_utc,
            )
            .scalar()
        )

        result_periods.append(
            PeriodTotalRead(
                period_start=start_utc,
                period_end=end_utc,
                total=total,
            )
        )

        end_local = start_local
        if start_local.month == 1:
            prev_year = start_local.year - 1
            prev_month = 12
        else:
            prev_year = start_local.year
            prev_month = start_local.month - 1

        start_local = datetime(prev_year, prev_month, billing_day, tzinfo=local_tz)

    return LastPeriodsHistoryRead(currency=currency, periods=result_periods)
