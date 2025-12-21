from typing import Annotated
from zoneinfo import ZoneInfo
from uuid import UUID
from datetime import date, timezone, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..helpers.wallets import ensure_wallet_member
from ..models import Product, User, Transaction, Category, Wallet
from ..schemas.transaction import TransactionRead, TransactionCreate

router = APIRouter(
    prefix="/wallets/{wallet_id}/transactions",
    tags=["transactions"],
)


@router.post("/", response_model=TransactionRead, status_code=201)
def create_transaction(
    wallet_id: UUID,
    body: TransactionCreate,
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
            status_code=400,
            detail="currency_base must equal wallet currency",
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

    product_id = body.product_id
    if product_id is not None:
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

        if product.category_id != body.category_id:
            raise HTTPException(
                status_code=400,
                detail="product does not belong to this category",
            )

    amount_original = body.amount_original
    currency_original = body.currency_original
    fx_rate = body.fx_rate

    fx_fields_set = sum(
        1 for v in (amount_original, currency_original, fx_rate) if v is not None
    )

    if fx_fields_set not in (0, 3):
        raise HTTPException(
            status_code=400,
            detail="Incomplete FX data: amount_original, currency_original and fx_rate must be all set or all null",
        )

    if currency_original is not None:
        currency_original = currency_original.upper()

    transaction = Transaction(
        wallet_id=wallet_id,
        user_id=current_user.id,
        category_id=body.category_id,
        product_id=product_id,
        type="expense",
        amount_base=body.amount_base,
        currency_base=currency_base,
        amount_original=amount_original,
        currency_original=currency_original,
        fx_rate=fx_rate,
        refund_of_transaction_id=None,
        occurred_at=body.occurred_at,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return TransactionRead.model_validate(transaction)


@router.get("/", response_model=list[TransactionRead], status_code=200)
def list_transactions(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    # filtry:
    from_date: date | None = None,
    to_date: date | None = None,
    current_period: bool = False,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    query = db.query(Transaction).filter(
        Transaction.wallet_id == wallet_id, Transaction.deleted_at.is_(None)
    )

    if current_period:
        settings = current_user.user_settings
        now_utc = datetime.now(timezone.utc)
        local_tz = ZoneInfo(settings.timezone)

        now_local = now_utc.astimezone(local_tz)
        today_local = now_local.date()
        billing_day = settings.billing_day

        year = today_local.year
        month = today_local.month

        if today_local.day >= billing_day:
            start_local = datetime(year, month, billing_day, tzinfo=local_tz)

            if month == 12:
                end_local = datetime(year + 1, 1, billing_day, tzinfo=local_tz)
            else:
                end_local = datetime(year, month + 1, billing_day, tzinfo=local_tz)
        else:
            end_local = datetime(year, month, billing_day, tzinfo=local_tz)

            if month == 1:
                start_local = datetime(year - 1, 12, billing_day, tzinfo=local_tz)
            else:
                start_local = datetime(year, month - 1, billing_day, tzinfo=local_tz)

        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)

        query = query.filter(
            Transaction.occurred_at >= start_utc, Transaction.occurred_at < end_utc
        )

    if not current_period and (from_date or to_date):
        settings = current_user.user_settings
        local_tz = ZoneInfo(settings.timezone)

        if from_date:
            start_local = datetime.combine(from_date, time.min, tzinfo=local_tz)
            start_utc = start_local.astimezone(timezone.utc)
            query = query.filter(Transaction.occurred_at >= start_utc)

        if to_date:
            end_local = datetime.combine(to_date, time.min, tzinfo=local_tz)
            end_local_next = end_local.replace(day=to_date.day) + timedelta(days=1)
            end_utc = end_local_next.astimezone(timezone.utc)
            query = query.filter(Transaction.occurred_at < end_utc)

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
            raise HTTPException(status_code=404, detail="category not found")

        query = query.filter(Transaction.category_id == category_id)

    if product_id is not None:

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

        query = query.filter(Transaction.product_id == product_id)

    transactions = query.order_by(
        Transaction.occurred_at.desc(), Transaction.created_at.desc()
    ).all()

    return [TransactionRead.model_validate(t) for t in transactions]
