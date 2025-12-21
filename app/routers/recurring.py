from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..helpers.wallets import ensure_wallet_member
from ..models import Product, User, RecurringTransaction, Category, Wallet
from ..schemas.recurring_transactions import (
    RecurringTransactionRead,
    RecurringTransactionCreate,
)

router = APIRouter(
    prefix="/wallets/{wallet_id}/recurring",
    tags=["recurring"],
)


@router.post("/", response_model=RecurringTransactionRead, status_code=201)
def create_recurring_transaction(
    wallet_id: UUID,
    body: RecurringTransactionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()

    if wallet is None:
        raise HTTPException(status_code=404, detail="wallet not found")
    currency_base = body.currency_base.upper()
    if currency_base != wallet.currency:
        raise HTTPException(
            status_code=400, detail="currency_base must equal wallet currency"
        )

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
        raise HTTPException(status_code=404, detail="category not found")

    if body.product_id:
        product = (
            db.query(Product)
            .filter(
                Product.id == body.product_id,
                Product.wallet_id == wallet_id,
                Product.deleted_at.is_(None),
            )
            .first()
        )
        if product is None:
            raise HTTPException(status_code=404, detail="product not found")
        if product.category_id != body.category_id:
            raise HTTPException(
                status_code=400, detail="product does not belong to this category"
            )
    recurring = RecurringTransaction(
        wallet_id=wallet_id,
        category_id=body.category_id,
        product_id=body.product_id,
        amount_base=body.amount_base,
        currency_base=currency_base,
        description=body.description,
        active=True,
    )

    db.add(recurring)
    db.commit()
    db.refresh(recurring)

    return RecurringTransactionRead.model_validate(recurring)
