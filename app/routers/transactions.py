import csv
import io
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db
from ..helpers.wallets import ensure_wallet_member
from ..models import Category, Product, Transaction, User, Wallet
from ..schemas.transaction import TransactionCreate, TransactionRead

router = APIRouter(
    prefix="/wallets/{wallet_id}/transactions",
    tags=["transactions"],
)


FX_TO_PLN: dict[str, Decimal] = {
    "PLN": Decimal("1"),
    "EUR": Decimal("4.30"),
    "USD": Decimal("3.95"),
}

TWOPLACES = Decimal("0.01")


def _q2(x: Decimal) -> Decimal:
    return x.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _normalize_currency(v: str) -> str:
    cur = (v or "").strip().upper()
    if len(cur) != 3:
        raise HTTPException(status_code=400, detail="currency must be a 3-letter code")
    return cur


def _get_rate_to_pln(cur: str) -> Decimal:
    if cur not in FX_TO_PLN:
        raise HTTPException(status_code=400, detail=f"Unsupported currency: {cur}")
    rate = FX_TO_PLN[cur]
    if rate <= 0:
        raise HTTPException(status_code=500, detail=f"Invalid FX_TO_PLN rate for {cur}")
    return rate


def _fx_rate(from_cur: str, to_cur: str) -> Decimal:
    if from_cur == to_cur:
        return Decimal("1")

    from_to_pln = _get_rate_to_pln(from_cur)
    to_to_pln = _get_rate_to_pln(to_cur)

    return from_to_pln / to_to_pln


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

    wallet_currency = _normalize_currency(wallet.currency)
    input_currency = _normalize_currency(body.currency)

    if body.amount is None:
        raise HTTPException(status_code=400, detail="amount is required")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be greater than 0")

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

    now_utc = datetime.now(timezone.utc)

    if input_currency == wallet_currency:
        amount_base = _q2(Decimal(body.amount))
        amount_original = None
        currency_original = None
        fx_rate = None
    else:
        rate = _fx_rate(input_currency, wallet_currency)

        amount_original = _q2(Decimal(body.amount))
        currency_original = input_currency
        fx_rate = _q2(rate)

        amount_base = _q2(amount_original * fx_rate)

    transaction = Transaction(
        wallet_id=wallet_id,
        user_id=current_user.id,
        category_id=body.category_id,
        product_id=body.product_id,
        type="expense",
        amount_base=amount_base,
        currency_base=wallet_currency,
        amount_original=amount_original,
        currency_original=currency_original,
        fx_rate=fx_rate,
        refund_of_transaction_id=None,
        occurred_at=now_utc,
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


@router.post(
    "/{transaction_id}/refund", response_model=TransactionRead, status_code=201
)
def refund_transaction(
    wallet_id: UUID,
    transaction_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    original = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.wallet_id == wallet_id,
            Transaction.deleted_at.is_(None),
        )
        .first()
    )

    if original is None:
        raise HTTPException(status_code=404, detail="transaction not found")

    if original.refund_of_transaction_id is not None:
        raise HTTPException(
            status_code=400, detail="Cannot refund a refund transaction"
        )
    if original.refunds:
        raise HTTPException(status_code=400, detail="Transaction already refunded")

    refund_amount_base = -original.amount_base
    if original.amount_original is not None:
        refund_amount_original = -original.amount_original
        refund_currency_original = original.currency_original
        refund_fx_rate = original.fx_rate
    else:
        refund_amount_original = None
        refund_currency_original = None
        refund_fx_rate = None

    refund = Transaction(
        wallet_id=wallet_id,
        user_id=current_user.id,
        category_id=original.category_id,
        product_id=original.product_id,
        type=original.type,
        amount_base=refund_amount_base,
        currency_base=original.currency_base,
        amount_original=refund_amount_original,
        currency_original=refund_currency_original,
        fx_rate=refund_fx_rate,
        occurred_at=datetime.now(timezone.utc),
        refund_of_transaction_id=original.id,
    )

    db.add(refund)
    db.commit()
    db.refresh(refund)

    return TransactionRead.model_validate(refund)


@router.delete("/{transaction_id}", status_code=204)
def soft_delete_transaction(
    wallet_id: UUID,
    transaction_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.wallet_id == wallet_id,
            Transaction.deleted_at.is_(None),
        )
        .first()
    )

    if transaction is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    if transaction.refunds:
        raise HTTPException(409, "Cannot delete transaction with refunds")

    transaction.deleted_at = datetime.now(timezone.utc)

    db.commit()
    return


@router.get("/export", status_code=200)
def export_transactions(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    format: str = "csv",
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    if format != "csv":
        raise HTTPException(status_code=400, detail="Only csv supported")

    settings = current_user.user_settings
    local_tz = ZoneInfo(settings.timezone)
    now_utc = datetime.now(timezone.utc)

    if current_period:
        now_local = now_utc.astimezone(local_tz)
        year = now_local.year
        month = now_local.month
        billing_day = settings.billing_day

        if now_local.day >= billing_day:
            period_start_local = datetime(year, month, billing_day, tzinfo=local_tz)
            if month == 12:
                period_end_local = datetime(year + 1, 1, billing_day, tzinfo=local_tz)
            else:
                period_end_local = datetime(
                    year, month + 1, billing_day, tzinfo=local_tz
                )
        else:
            period_end_local = datetime(year, month, billing_day, tzinfo=local_tz)
            if month == 1:
                period_start_local = datetime(
                    year - 1, 12, billing_day, tzinfo=local_tz
                )
            else:
                period_start_local = datetime(
                    year, month - 1, billing_day, tzinfo=local_tz
                )

        period_start_utc = period_start_local.astimezone(timezone.utc)
        period_end_utc = period_end_local.astimezone(timezone.utc)
    else:
        period_start_utc = datetime(1970, 1, 1, tzinfo=timezone.utc)
        period_end_utc = now_utc

        if from_date is not None:
            start_local = datetime.combine(from_date, time.min, tzinfo=local_tz)
            period_start_utc = start_local.astimezone(timezone.utc)

        if to_date is not None:
            end_local_exclusive = datetime.combine(
                to_date, time.min, tzinfo=local_tz
            ) + timedelta(days=1)
            period_end_utc = end_local_exclusive.astimezone(timezone.utc)

    query = db.query(Transaction).filter(
        Transaction.wallet_id == wallet_id,
        Transaction.deleted_at.is_(None),
        Transaction.occurred_at >= period_start_utc,
        Transaction.occurred_at < period_end_utc,
        Transaction.type == "expense",
    )
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if product_id:
        query = query.filter(Transaction.product_id == product_id)

    query = query.options(
        joinedload(Transaction.category),
        joinedload(Transaction.product),
    ).order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc())

    def iter_csv():
        yield "\ufeff"

        buf = io.StringIO()
        writer = csv.writer(buf)

        writer.writerow(
            [
                "transaction_id",
                "occurred_at",
                "amount_base",
                "currency_base",
                "category_id",
                "category_name",
                "product_id",
                "product_name",
                "amount_original",
                "currency_original",
                "fx_rate",
                "refund_of_transaction_id",
                "created_at",
            ]
        )
        yield buf.getvalue()
        _ = buf.seek(0)
        _ = buf.truncate(0)

        for t in query.yield_per(1000):
            writer.writerow(
                [
                    str(t.id),
                    t.occurred_at.isoformat(),
                    str(t.amount_base),
                    t.currency_base,
                    str(t.category_id),
                    t.category.name if t.category else "",
                    str(t.product_id) if t.product_id else "",
                    t.product.name if t.product else "",
                    str(t.amount_original) if t.amount_original is not None else "",
                    t.currency_original or "",
                    str(t.fx_rate) if t.fx_rate is not None else "",
                    (
                        str(t.refund_of_transaction_id)
                        if t.refund_of_transaction_id
                        else ""
                    ),
                    t.created_at.isoformat(),
                ]
            )
            yield buf.getvalue()
            _ = buf.seek(0)
            _ = buf.truncate(0)

    filename = f"transactions_{wallet_id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
