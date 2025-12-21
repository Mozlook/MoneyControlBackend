from typing import Annotated
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import RecurringTransaction, User, Product, Category, Transaction
from ..schemas.product import ProductCreate, ProductRead
from ..helpers.wallets import ensure_wallet_member

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
