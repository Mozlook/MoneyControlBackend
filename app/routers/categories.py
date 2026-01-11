from typing import Annotated
from uuid import UUID
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import RecurringTransaction, User, Category, Transaction
from ..schemas.category import CategoryCreate, CategoryRead, CategoryReadSum
from ..helpers.wallets import ensure_wallet_member
from ..helpers.periods import resolve_period_range_utc

router = APIRouter(
    prefix="/wallets/{wallet_id}/categories",
    tags=["categories"],
)


@router.post("/", response_model=CategoryRead, status_code=201)
def create_category(
    wallet_id: UUID,
    body: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    existing = (
        db.query(Category)
        .filter(
            Category.wallet_id == wallet_id,
            Category.name == body.name,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Category with this name already exists in this wallet",
        )

    category = Category(
        wallet_id=wallet_id,
        name=body.name,
        color=body.color,
        icon=body.icon,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return CategoryRead.model_validate(category)


@router.get("/", response_model=list[CategoryRead], status_code=200)
def list_category(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    categories = (
        db.query(Category)
        .filter(Category.wallet_id == wallet_id, Category.deleted_at.is_(None))
        .order_by(Category.created_at)
        .all()
    )

    return [CategoryRead.model_validate(c) for c in categories]


@router.delete("/{category_id}", status_code=204)
def soft_delete_category(
    wallet_id: UUID,
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    category = (
        db.query(Category)
        .filter(Category.wallet_id == wallet_id, Category.id == category_id)
        .first()
    )

    if category is None or category.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Category not found")

    category.deleted_at = datetime.now(timezone.utc)

    db.commit()
    return


@router.delete("/{category_id}/hard", status_code=204)
def hard_delete_category(
    wallet_id: UUID,
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.wallet_id == wallet_id)
        .first()
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.deleted_at is None:
        raise HTTPException(status_code=409, detail="soft delete category first")

    transactions = (
        db.query(Transaction).filter(Transaction.category_id == category_id).all()
    )

    recurring_transactions = (
        db.query(RecurringTransaction)
        .filter(RecurringTransaction.category_id == category_id)
        .all()
    )

    if transactions or recurring_transactions:
        raise HTTPException(
            status_code=409,
            detail="Category is still used in transactions and cannot be hard deleted",
        )

    db.delete(category)
    db.commit()
    return


@router.get("/with-sum/", response_model=list[CategoryReadSum], status_code=200)
def list_categories_with_sum(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    # query params – wszystko opcjonalne / z defaultami
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    include_empty: bool = True,
) -> list[CategoryReadSum]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    settings = current_user.user_settings
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
            Transaction.wallet_id == wallet_id,
            Transaction.deleted_at.is_(None),
            Transaction.occurred_at >= pr.period_start_utc,
            Transaction.occurred_at < pr.period_end_utc,
        )
        .group_by(Transaction.category_id)
        .subquery()
    )

    period_sum_col = func.coalesce(tx_sum_sq.c.period_sum, Decimal("0")).label(
        "period_sum"
    )

    q = (
        db.query(Category, period_sum_col)
        .outerjoin(tx_sum_sq, tx_sum_sq.c.category_id == Category.id)
        .filter(
            Category.wallet_id == wallet_id,
            Category.deleted_at.is_(None),
        )
        .order_by(Category.name.asc())
    )

    if not include_empty:
        q = q.filter(period_sum_col != 0)

    rows = q.all()

    out: list[CategoryReadSum] = []
    for cat, period_sum in rows:
        base = CategoryRead.model_validate(cat).model_dump()
        base["period_sum"] = period_sum
        out.append(CategoryReadSum(**base))

    return out
