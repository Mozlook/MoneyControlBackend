from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlmodel import col

from ..models import Transaction


def get_transaction_or_404(
    db: Session,
    *,
    wallet_id: UUID,
    transaction_id: UUID,
) -> Transaction:
    tx = (
        db.query(Transaction)
        .filter(
            col(Transaction.wallet_id) == wallet_id,
            col(Transaction.id) == transaction_id,
            col(Transaction.deleted_at).is_(None),
        )
        .first()
    )
    if tx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="transaction not found"
        )
    return tx


def ensure_refundable(tx: Transaction) -> None:
    if tx.refund_of_transaction_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot refund a refund transaction",
        )
    if tx.refunds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction already refunded",
        )


def ensure_deletable(tx: Transaction) -> None:
    if tx.refunds:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete transaction with refunds",
        )


def base_transactions_q(db: Session, *, wallet_id: UUID):
    return (
        db.query(Transaction)
        .options(selectinload(Transaction.category), selectinload(Transaction.product))
        .filter(
            col(Transaction.wallet_id) == wallet_id,
            col(Transaction.deleted_at).is_(None),
        )
    )
