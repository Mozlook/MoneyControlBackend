from __future__ import annotations

from datetime import date
from datetime import datetime
from uuid import UUID
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlmodel import col

from ..models import Transaction
from ..models import User
from ..helpers.periods import resolve_period_range_utc
from ..helpers.users import require_user_settings


from typing import TypeAlias
from collections.abc import Iterable

AggRow: TypeAlias = tuple[UUID, UUID | None, Decimal]

SumsResult: TypeAlias = tuple[
    defaultdict[UUID, Decimal],
    defaultdict[UUID, Decimal],
    dict[tuple[UUID, UUID], Decimal],
    set[UUID],
    set[UUID],
    Decimal,
]


def _zero() -> Decimal:
    return Decimal("0")


def resolve_user_period_range(
    *,
    user: User,
    current_period: bool,
    from_date: date | None,
    to_date: date | None,
):
    settings = require_user_settings(user)
    return resolve_period_range_utc(
        billing_day=settings.billing_day,
        timezone_name=settings.timezone,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
    )


def expense_transactions_in_period_q(
    db: Session,
    *,
    wallet_id: UUID,
    period_start_utc: datetime,
    period_end_utc: datetime,
):
    return db.query(Transaction).filter(
        col(Transaction.wallet_id) == wallet_id,
        col(Transaction.deleted_at).is_(None),
        col(Transaction.type) == "expense",
        col(Transaction.occurred_at) >= period_start_utc,
        col(Transaction.occurred_at) < period_end_utc,
    )


def build_category_product_sums(agg_rows: Iterable[AggRow]) -> SumsResult:
    category_sum: defaultdict[UUID, Decimal] = defaultdict(_zero)
    no_product_sum: defaultdict[UUID, Decimal] = defaultdict(_zero)
    product_sum: dict[tuple[UUID, UUID], Decimal] = {}
    used_category_ids: set[UUID] = set()
    used_product_ids: set[UUID] = set()
    total: Decimal = Decimal("0")

    for cat_id, prod_id, sum_amount in agg_rows:
        used_category_ids.add(cat_id)
        category_sum[cat_id] += sum_amount
        total += sum_amount

        if prod_id is None:
            no_product_sum[cat_id] += sum_amount
        else:
            used_product_ids.add(prod_id)
            product_sum[(cat_id, prod_id)] = sum_amount

    return (
        category_sum,
        no_product_sum,
        product_sum,
        used_category_ids,
        used_product_ids,
        total,
    )
