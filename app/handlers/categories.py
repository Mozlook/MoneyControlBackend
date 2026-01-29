from uuid import UUID
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlmodel import col

from ..models import RecurringTransaction, User, Category, Transaction
from ..schemas.category import CategoryCreate, CategoryRead, CategoryReadSum
from ..helpers.wallets import ensure_wallet_member
from ..helpers.periods import resolve_period_range_utc
from ..helpers.categories import (
    ensure_category_name_unique,
    get_category_or_404,
    soft_delete_now,
)
from ..helpers.users import require_user_settings


def create_category(
    *, wallet_id: UUID, body: CategoryCreate, db: Session, current_user: User
) -> CategoryRead:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    ensure_category_name_unique(db, wallet_id=wallet_id, name=body.name)

    category = Category(
        wallet_id=wallet_id, name=body.name, color=body.color, icon=body.icon
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category)


def list_categories(
    *, wallet_id: UUID, db: Session, current_user: User, deleted: bool = False
) -> list[CategoryRead]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    q = db.query(Category).filter(col(Category.wallet_id) == wallet_id)
    q = (
        q.filter(col(Category.deleted_at).isnot(None))
        if deleted
        else q.filter(col(Category.deleted_at).is_(None))
    )

    return [
        CategoryRead.model_validate(c)
        for c in q.order_by(col(Category.created_at)).all()
    ]


def soft_delete_category(
    *, wallet_id: UUID, category_id: UUID, db: Session, current_user: User
) -> None:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    category = get_category_or_404(
        db, wallet_id=wallet_id, category_id=category_id, require_not_deleted=True
    )
    soft_delete_now(category)

    db.commit()


def hard_delete_category(
    *, wallet_id: UUID, category_id: UUID, db: Session, current_user: User
) -> None:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    category = get_category_or_404(
        db, wallet_id=wallet_id, category_id=category_id, require_not_deleted=False
    )

    has_tx = (
        db.query(Transaction)
        .filter(col(Transaction.category_id) == category_id)
        .first()
        is not None
    )
    has_rtx = (
        db.query(RecurringTransaction)
        .filter(col(RecurringTransaction.category_id) == category_id)
        .first()
        is not None
    )

    if has_tx or has_rtx:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category is still used in transactions and cannot be hard deleted",
        )

    db.delete(category)
    db.commit()


def list_categories_with_sum(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    include_empty: bool = True,
) -> list[CategoryReadSum]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    settings = require_user_settings(current_user)
    pr = resolve_period_range_utc(
        billing_day=settings.billing_day,
        timezone_name=settings.timezone,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
    )

    tx_sum_sq = (
        db.query(
            Transaction.category_id.label("category_id"),
            func.sum(Transaction.amount_base).label("period_sum"),
        )
        .filter(
            col(Transaction.wallet_id) == wallet_id,
            col(Transaction.deleted_at).is_(None),
            col(Transaction.occurred_at) >= pr.period_start_utc,
            col(Transaction.occurred_at) < pr.period_end_utc,
        )
        .group_by(col(Transaction.category_id))
        .subquery()
    )

    period_sum_col = func.coalesce(tx_sum_sq.c.period_sum, Decimal("0")).label(
        "period_sum"
    )

    q = (
        db.query(Category, period_sum_col)
        .outerjoin(tx_sum_sq, tx_sum_sq.c.category_id == Category.id)
        .filter(
            col(Category.wallet_id) == wallet_id, col(Category.deleted_at).is_(None)
        )
        .order_by(col(Category.name).asc())
    )

    if not include_empty:
        q = q.filter(period_sum_col != 0)

    rows = q.all()
    out: list[CategoryReadSum] = []
    for cat, period_sum in rows:
        base = CategoryRead.model_validate(cat).model_dump()
        out.append(CategoryReadSum(**(base | {"period_sum": period_sum})))
    return out
