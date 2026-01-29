from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload
from sqlmodel import col

from ..helpers.wallets import ensure_wallet_member
from ..helpers.periods import resolve_period_range_utc
from ..helpers.categories import get_category_or_404
from ..helpers.products import get_product_or_404
from ..helpers.recurring import (
    ensure_currency_matches_wallet,
    get_recurring_or_404,
    utcnow,
)
from ..models import RecurringTransaction, Transaction, User
from ..schemas.recurring_transactions import (
    RecurringTransactionCreate,
    RecurringTransactionRead,
)
from ..schemas.transaction import TransactionRead


def create_recurring_transaction(
    *,
    wallet_id: UUID,
    body: RecurringTransactionCreate,
    db: Session,
    current_user: User,
) -> RecurringTransactionRead:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    wallet_currency = membership.wallet.currency

    currency_base = ensure_currency_matches_wallet(
        currency_base=body.currency_base,
        wallet_currency=wallet_currency,
    )

    category = get_category_or_404(
        db=db,
        wallet_id=wallet_id,
        category_id=body.category_id,
        require_not_deleted=True,
    )

    if body.product_id is not None:
        product = get_product_or_404(
            db=db,
            wallet_id=wallet_id,
            product_id=body.product_id,
            require_not_deleted=True,
        )
        if product.category_id != category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="product does not belong to this category",
            )

    recurring = RecurringTransaction(
        wallet_id=wallet_id,
        category_id=body.category_id,
        product_id=body.product_id,
        amount_base=body.amount_base,
        currency_base=currency_base,
        description=body.description,
        active=True,
        updated_at=utcnow(),
    )

    db.add(recurring)
    db.commit()

    recurring = (
        db.query(RecurringTransaction)
        .options(
            selectinload(RecurringTransaction.category),
            selectinload(RecurringTransaction.product),
        )
        .filter(
            col(RecurringTransaction.wallet_id) == wallet_id,
            col(RecurringTransaction.id) == recurring.id,
        )
        .one()
    )

    return RecurringTransactionRead.model_validate(recurring)


def list_recurring_transactions(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    active: bool | None = None,
) -> list[RecurringTransactionRead]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    query = (
        db.query(RecurringTransaction)
        .options(
            selectinload(RecurringTransaction.category),
            selectinload(RecurringTransaction.product),
        )
        .filter(col(RecurringTransaction.wallet_id) == wallet_id)
    )

    if active is not None:
        query = query.filter(col(RecurringTransaction.active) == active)

    recurrings = query.order_by(col(RecurringTransaction.created_at)).all()
    return [RecurringTransactionRead.model_validate(r) for r in recurrings]


def apply_recurring_transactions(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
) -> list[TransactionRead]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    settings = current_user.user_settings
    if settings is None:
        raise HTTPException(status_code=500, detail="User settings missing")

    pr = resolve_period_range_utc(
        billing_day=settings.billing_day,
        timezone_name=settings.timezone,
        current_period=True,
    )
    period_start_utc = pr.period_start_utc

    now_utc = datetime.now(timezone.utc)

    recurrings = (
        db.query(RecurringTransaction)
        .filter(
            col(RecurringTransaction.wallet_id) == wallet_id,
            col(RecurringTransaction.active).is_(True),
            or_(
                col(RecurringTransaction.last_applied_at).is_(None),
                col(RecurringTransaction.last_applied_at) < period_start_utc,
            ),
        )
        .all()
    )

    if not recurrings:
        return []

    created_ids: list[UUID] = []

    for r in recurrings:
        tx = Transaction(
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
        db.add(tx)
        created_ids.append(tx.id)

        r.last_applied_at = now_utc
        r.updated_at = now_utc

    db.commit()

    created_txs = (
        db.query(Transaction)
        .options(
            selectinload(Transaction.category),
            selectinload(Transaction.product),
        )
        .filter(
            col(Transaction.wallet_id) == wallet_id,
            col(Transaction.id).in_(created_ids),
        )
        .all()
    )

    by_id = {t.id: t for t in created_txs}
    ordered = [by_id[tid] for tid in created_ids if tid in by_id]
    return [TransactionRead.model_validate(t) for t in ordered]


def update_recurring_transaction(
    *,
    wallet_id: UUID,
    recurring_id: UUID,
    body: RecurringTransactionCreate,
    db: Session,
    current_user: User,
) -> RecurringTransactionRead:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    wallet_currency = membership.wallet.currency

    recurring = get_recurring_or_404(db, wallet_id=wallet_id, recurring_id=recurring_id)

    currency_base = ensure_currency_matches_wallet(
        currency_base=body.currency_base,
        wallet_currency=wallet_currency,
    )

    category = get_category_or_404(
        db=db,
        wallet_id=wallet_id,
        category_id=body.category_id,
        require_not_deleted=True,
    )

    if body.product_id is not None:
        product = get_product_or_404(
            db=db,
            wallet_id=wallet_id,
            product_id=body.product_id,
            require_not_deleted=True,
        )
        if product.category_id != category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="product does not belong to this category",
            )

    recurring.category_id = body.category_id
    recurring.product_id = body.product_id
    recurring.amount_base = body.amount_base
    recurring.currency_base = currency_base
    recurring.description = body.description
    recurring.updated_at = utcnow()

    db.commit()

    recurring = (
        db.query(RecurringTransaction)
        .options(
            selectinload(RecurringTransaction.category),
            selectinload(RecurringTransaction.product),
        )
        .filter(
            col(RecurringTransaction.wallet_id) == wallet_id,
            col(RecurringTransaction.id) == recurring_id,
        )
        .one()
    )

    return RecurringTransactionRead.model_validate(recurring)


def deactivate_recurring_transaction(
    *,
    wallet_id: UUID,
    recurring_id: UUID,
    db: Session,
    current_user: User,
) -> None:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    recurring = get_recurring_or_404(
        db,
        wallet_id=wallet_id,
        recurring_id=recurring_id,
        require_active=True,
    )

    recurring.active = False
    recurring.updated_at = utcnow()
    db.commit()


def activate_recurring_transaction(
    *,
    wallet_id: UUID,
    recurring_id: UUID,
    db: Session,
    current_user: User,
) -> None:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    recurring = get_recurring_or_404(
        db,
        wallet_id=wallet_id,
        recurring_id=recurring_id,
        require_active=None,
    )

    recurring.active = True
    recurring.updated_at = utcnow()
    db.commit()
