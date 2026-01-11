from typing import Annotated
from uuid import UUID
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..deps import get_db, get_current_user
from ..models import RecurringTransaction, User, Product, Category, Transaction
from ..schemas.product import ProductCreate, ProductRead, ProductReadSum
from ..helpers.wallets import ensure_wallet_member
from ..helpers.periods import resolve_period_range_utc

router = APIRouter(
    prefix="/wallets/{wallet_id}/products",
    tags=["products"],
)


@router.post("/", response_model=ProductRead, status_code=201)
def create_product(
    wallet_id: UUID,
    body: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    category = (
        db.query(Category)
        .filter(
            Category.id == body.category_id,
            Category.wallet_id == wallet_id,
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        wallet_id=wallet_id,
        category_id=body.category_id,
        name=body.name,
        importance=body.importance,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return ProductRead.model_validate(product)


@router.get("/", response_model=list[ProductRead], status_code=200)
def list_products(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    category_id: UUID | None = None,
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    query = db.query(Product).filter(
        Product.wallet_id == wallet_id,
        Product.deleted_at.is_(None),
    )

    if category_id is not None:
        category = (
            db.query(Category)
            .filter(
                Category.id == category_id,
                Category.wallet_id == wallet_id,
                Category.deleted_at.is_(None),
            )
            .first()
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        query = query.filter(Product.category_id == category_id)

    products = query.order_by(Product.created_at).all()

    return [ProductRead.model_validate(p) for p in products]


@router.delete("/{product_id}", status_code=204)
def soft_delete_product(
    wallet_id: UUID,
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.wallet_id == wallet_id,
            Product.deleted_at.is_(None),
        )
        .first()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

    transactions = (
        db.query(Transaction).filter(Transaction.product_id == product_id).all()
    )
    for t in transactions:
        t.product_id = None

    recurringTransactions = (
        db.query(RecurringTransaction)
        .filter(RecurringTransaction.product_id == product_id)
        .all()
    )
    for rt in recurringTransactions:
        rt.product_id = None

    product.deleted_at = datetime.now(timezone.utc)

    db.commit()

    return


@router.delete("/{product_id}/hard", status_code=204)
def hard_delete_product(
    wallet_id: UUID,
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.wallet_id == wallet_id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.deleted_at is None:
        raise HTTPException(status_code=409, detail="soft delete product first")

    transactions = (
        db.query(Transaction).filter(Transaction.product_id == product_id).all()
    )

    recurring_transactions = (
        db.query(RecurringTransaction)
        .filter(RecurringTransaction.product_id == product_id)
        .all()
    )

    if transactions or recurring_transactions:
        raise HTTPException(
            status_code=409,
            detail="Product is still used in transactions and cannot be hard deleted",
        )

    db.delete(product)
    db.commit()
    return


@router.get("/with-sum/", response_model=list[ProductReadSum], status_code=200)
def list_products_with_sum(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    category_id: UUID | None = None,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[ProductReadSum]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    if category_id is not None:
        category = (
            db.query(Category)
            .filter(
                Category.id == category_id,
                Category.wallet_id == wallet_id,
                Category.deleted_at.is_(None),
            )
            .first()
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

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
