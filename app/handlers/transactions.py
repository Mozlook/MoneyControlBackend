import csv
import io
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

from ..helpers.wallets import ensure_wallet_member
from ..helpers.categories import get_category_or_404
from ..helpers.products import get_product_or_404
from ..helpers.summary import resolve_user_period_range
from ..helpers.fx import normalize_currency, compute_amounts
from ..helpers.transactions import (
    base_transactions_q,
    ensure_deletable,
    ensure_refundable,
    get_transaction_or_404,
)
from ..models import Transaction, User
from ..schemas.transaction import TransactionCreate, TransactionRead


def create_transaction(
    *,
    wallet_id: UUID,
    body: TransactionCreate,
    db: Session,
    current_user: User,
) -> TransactionRead:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    wallet_currency = normalize_currency(membership.wallet.currency)

    amount = body.amount
    if not amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="amount is required"
        )
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount must be greater than 0",
        )

    input_currency = normalize_currency(body.currency)

    category = get_category_or_404(
        db=db,
        wallet_id=wallet_id,
        category_id=body.category_id,
        require_not_deleted=True,
    )

    product_id: UUID | None = body.product_id
    if product_id is not None:
        product = get_product_or_404(
            db=db,
            wallet_id=wallet_id,
            product_id=product_id,
            require_not_deleted=True,
        )
        if product.category_id != category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="product does not belong to this category",
            )

    (
        amount_base,
        currency_base,
        amount_original,
        currency_original,
        fx_rate,
    ) = compute_amounts(
        amount=amount,
        input_currency=input_currency,
        wallet_currency=wallet_currency,
    )

    now_utc = datetime.now(timezone.utc)
    occurred_at = (
        body.occurred_at if getattr(body, "occurred_at", None) is not None else now_utc
    )

    transaction = Transaction(
        wallet_id=wallet_id,
        user_id=current_user.id,
        category_id=body.category_id,
        product_id=product_id,
        type="expense",
        amount_base=amount_base,
        currency_base=currency_base,
        amount_original=amount_original,
        currency_original=currency_original,
        fx_rate=fx_rate,
        refund_of_transaction_id=None,
        occurred_at=occurred_at,
    )

    db.add(transaction)
    db.commit()

    transaction = (
        base_transactions_q(db, wallet_id=wallet_id)
        .filter(col(Transaction.id) == transaction.id)
        .one()
    )

    return TransactionRead.model_validate(transaction)


def list_transactions(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    from_date: date | None = None,
    to_date: date | None = None,
    current_period: bool = False,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
) -> list[TransactionRead]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    query = base_transactions_q(db, wallet_id=wallet_id)

    if current_period or from_date is not None or to_date is not None:
        period = resolve_user_period_range(
            user=current_user,
            current_period=current_period,
            from_date=from_date,
            to_date=to_date,
        )
        query = query.filter(
            col(Transaction.occurred_at) >= period.period_start_utc,
            col(Transaction.occurred_at) < period.period_end_utc,
        )

    if category_id is not None:
        _ = get_category_or_404(
            db=db,
            wallet_id=wallet_id,
            category_id=category_id,
            require_not_deleted=True,
        )
        query = query.filter(col(Transaction.category_id) == category_id)

    if product_id is not None:
        _ = get_product_or_404(
            db=db,
            wallet_id=wallet_id,
            product_id=product_id,
            require_not_deleted=True,
        )
        query = query.filter(col(Transaction.product_id) == product_id)

    transactions = query.order_by(
        col(Transaction.occurred_at).desc(), col(Transaction.created_at).desc()
    ).all()

    return [TransactionRead.model_validate(t) for t in transactions]


def refund_transaction(
    *,
    wallet_id: UUID,
    transaction_id: UUID,
    db: Session,
    current_user: User,
) -> TransactionRead:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    original = get_transaction_or_404(
        db, wallet_id=wallet_id, transaction_id=transaction_id
    )
    ensure_refundable(original)

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

    refund = (
        base_transactions_q(db, wallet_id=wallet_id)
        .filter(col(Transaction.id) == refund.id)
        .one()
    )

    return TransactionRead.model_validate(refund)


def soft_delete_transaction(
    *,
    wallet_id: UUID,
    transaction_id: UUID,
    db: Session,
    current_user: User,
) -> None:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    tx = get_transaction_or_404(db, wallet_id=wallet_id, transaction_id=transaction_id)
    ensure_deletable(tx)

    tx.deleted_at = datetime.now(timezone.utc)
    db.commit()


def export_transactions(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    format: str = "csv",
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
) -> StreamingResponse:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    if format != "csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only csv supported"
        )

    period = resolve_user_period_range(
        user=current_user,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
    )

    query = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.category),
            joinedload(Transaction.product),
        )
        .filter(
            col(Transaction.wallet_id) == wallet_id,
            col(Transaction.deleted_at).is_(None),
            col(Transaction.type) == "expense",
            col(Transaction.occurred_at) >= period.period_start_utc,
            col(Transaction.occurred_at) < period.period_end_utc,
        )
    )

    if category_id is not None:
        _ = get_category_or_404(
            db=db,
            wallet_id=wallet_id,
            category_id=category_id,
            require_not_deleted=True,
        )
        query = query.filter(col(Transaction.category_id) == category_id)

    if product_id is not None:
        _ = get_product_or_404(
            db=db,
            wallet_id=wallet_id,
            product_id=product_id,
            require_not_deleted=True,
        )
        query = query.filter(col(Transaction.product_id) == product_id)

    query = query.order_by(
        col(Transaction.occurred_at).desc(), col(Transaction.created_at).desc()
    )

    def iter_csv():
        # BOM dla Excela
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
