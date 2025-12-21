from datetime import timezone, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..deps import get_db, get_current_user
from ..helpers.wallets import ensure_wallet_member
from ..models import Product, User, RecurringTransaction, Category, Wallet, Transaction
from ..schemas.recurring_transactions import (
    RecurringTransactionRead,
    RecurringTransactionCreate,
)
from ..schemas.transaction import TransactionRead

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


@router.get("/", response_model=list[RecurringTransactionRead], status_code=200)
def list_recurring_transactions(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    active: bool | None = None,
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    query = db.query(RecurringTransaction).filter(
        RecurringTransaction.wallet_id == wallet_id
    )

    if active is not None:
        query = query.filter(RecurringTransaction.active == active)
    recurrings = query.order_by(RecurringTransaction.created_at).all()

    return [RecurringTransactionRead.model_validate(r) for r in recurrings]


@router.post("/apply", response_model=list[TransactionRead], status_code=201)
def apply_recurring_transactions(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    settings = current_user.user_settings

    now_utc = datetime.now(timezone.utc)
    local_tz = ZoneInfo(settings.timezone)
    now_local = now_utc.astimezone(local_tz)
    billing_day = settings.billing_day

    year = now_local.year
    month = now_local.month
    if now_local.day >= billing_day:
        start_local = datetime(year, month, billing_day, tzinfo=local_tz)

    else:

        if month == 1:
            start_local = datetime(year - 1, 12, billing_day, tzinfo=local_tz)
        else:
            start_local = datetime(year, month - 1, billing_day, tzinfo=local_tz)

    start_utc = start_local.astimezone(timezone.utc)

    query = db.query(RecurringTransaction).filter(
        RecurringTransaction.wallet_id == wallet_id, RecurringTransaction.active
    )

    recurring = query.filter(
        or_(
            RecurringTransaction.last_applied_at.is_(None),
            RecurringTransaction.last_applied_at < start_utc,
        )
    ).all()

    transactions: list[Transaction] = []
    for r in recurring:
        transaction = Transaction(
            wallet_id=wallet_id,
            user_id=current_user.id,
            category_id=r.category_id,
            product_id=r.product_id,
            type="expense",
            amount_base=r.amount_base,
            currency_base=r.currency_base,
            amount_original=None,
            currency_original=None,
            fx_rate=None,
            occurred_at=now_utc,
            refund_of_transaction_id=None,
        )

        db.add(transaction)
        r.last_applied_at = now_utc
        r.updated_at = now_utc
        transactions.append(transaction)
    db.commit()

    return [TransactionRead.model_validate(t) for t in transactions]
