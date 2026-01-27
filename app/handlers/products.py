from uuid import UUID
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from ..models import RecurringTransaction, User, Product, Transaction
from ..schemas.product import ProductCreate, ProductRead, ProductReadSum
from ..helpers.wallets import ensure_wallet_member
from ..helpers.periods import resolve_period_range_utc
from ..helpers.categories import get_category_or_404
from ..helpers.products import (
    get_product_or_404,
    soft_delete_now,
)
from ..helpers.product_refs import unlink_product_references


def create_product(
    *,
    wallet_id: UUID,
    body: ProductCreate,
    db: Session,
    current_user: User,
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    _ = get_category_or_404(
        db=db,
        wallet_id=wallet_id,
        category_id=body.category_id,
        require_not_deleted=True,
    )

    product = Product(
        wallet_id=wallet_id,
        category_id=body.category_id,
        name=body.name,
        importance=body.importance,
    )

    db.add(product)
    db.commit()
    product = (
        db.query(Product)
        .options(selectinload(Product.category))
        .filter(Product.id == product.id)
        .one()
    )
    return ProductRead.model_validate(product)


def list_products(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    category_id: UUID | None = None,
    deleted: bool = False,
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    query = (
        db.query(Product)
        .filter(
            Product.wallet_id == wallet_id,
        )
        .options(selectinload(Product.category))
    )

    if deleted:
        query = query.filter(Product.deleted_at.isnot(None))
    else:
        query = query.filter(Product.deleted_at.is_(None))

    if category_id is not None:
        _ = get_category_or_404(
            db=db,
            wallet_id=wallet_id,
            category_id=category_id,
            require_not_deleted=True,
        )

        query = query.filter(Product.category_id == category_id)
    products = query.order_by(Product.created_at).all()

    return [ProductRead.model_validate(p) for p in products]


def soft_delete_product(
    *, wallet_id: UUID, product_id: UUID, db: Session, current_user: User
) -> None:
    ensure_wallet_member(db, wallet_id, current_user)

    product = get_product_or_404(
        db, wallet_id=wallet_id, product_id=product_id, require_not_deleted=True
    )

    unlink_product_references(db, wallet_id=wallet_id, product_id=product_id)
    soft_delete_now(product)

    db.commit()


def hard_delete_product(
    *, wallet_id: UUID, product_id: UUID, db: Session, current_user: User
) -> None:
    ensure_wallet_member(db, wallet_id, current_user)

    product = get_product_or_404(
        db, wallet_id=wallet_id, product_id=product_id, require_not_deleted=False
    )

    has_tx = (
        db.query(Transaction.id)
        .filter(
            Transaction.wallet_id == wallet_id, Transaction.product_id == product_id
        )
        .first()
        is not None
    )
    has_rtx = (
        db.query(RecurringTransaction.id)
        .filter(
            RecurringTransaction.wallet_id == wallet_id,
            RecurringTransaction.product_id == product_id,
        )
        .first()
        is not None
    )

    if has_tx or has_rtx:
        raise HTTPException(
            status_code=409,
            detail="Product is still used in transactions and cannot be hard deleted",
        )

    db.delete(product)
    db.commit()


def list_products_with_sum(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    category_id: UUID | None = None,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[ProductReadSum]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    if category_id is not None:
        _ = get_category_or_404(
            db=db,
            wallet_id=wallet_id,
            category_id=category_id,
            require_not_deleted=True,
        )

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
            Transaction.product_id.label("product_id"),
            func.sum(Transaction.amount_base).label("period_sum"),
        )
        .filter(
            Transaction.wallet_id == wallet_id,
            Transaction.deleted_at.is_(None),
            Transaction.product_id.isnot(None),
            Transaction.occurred_at >= pr.period_start_utc,
            Transaction.occurred_at < pr.period_end_utc,
        )
        .group_by(Transaction.product_id)
        .subquery()
    )

    products_q = (
        db.query(
            Product,
            func.coalesce(tx_sum_sq.c.period_sum, Decimal("0")).label("period_sum"),
        )
        .outerjoin(tx_sum_sq, tx_sum_sq.c.product_id == Product.id)
        .options(joinedload(Product.category))
        .filter(
            Product.wallet_id == wallet_id,
            Product.deleted_at.is_(None),
        )
    )

    if category_id is not None:
        products_q = products_q.filter(Product.category_id == category_id)

    rows = products_q.order_by(Product.name.asc()).all()

    out: list[ProductReadSum] = []
    for prod, period_sum in rows:
        base = ProductRead.model_validate(prod).model_dump()
        base["period_sum"] = period_sum
        out.append(ProductReadSum(**base))

    return out
