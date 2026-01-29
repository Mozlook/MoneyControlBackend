from sqlalchemy.orm import Session
from uuid import UUID
from ..models import Transaction, RecurringTransaction
from sqlmodel import col


def unlink_product_references(
    db: Session,
    *,
    wallet_id: UUID,
    product_id: UUID,
) -> None:

    _ = (
        db.query(Transaction)
        .filter(
            col(Transaction.wallet_id) == wallet_id,
            col(Transaction.product_id) == product_id,
        )
        .update({col(Transaction.product_id): None}, synchronize_session=False)
    )

    _ = (
        db.query(RecurringTransaction)
        .filter(
            col(RecurringTransaction.wallet_id) == wallet_id,
            col(RecurringTransaction.product_id) == product_id,
        )
        .update({col(RecurringTransaction.product_id): None}, synchronize_session=False)
    )
