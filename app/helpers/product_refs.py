from sqlalchemy.orm import Session
from uuid import UUID
from ..models import Transaction, RecurringTransaction


def unlink_product_references(
    db: Session,
    *,
    wallet_id: UUID,
    product_id: UUID,
) -> None:
    (
        db.query(Transaction)
        .filter(
            Transaction.wallet_id == wallet_id, Transaction.product_id == product_id
        )
        .update({Transaction.product_id: None}, synchronize_session=False)
    )

    (
        db.query(RecurringTransaction)
        .filter(
            RecurringTransaction.wallet_id == wallet_id,
            RecurringTransaction.product_id == product_id,
        )
        .update({RecurringTransaction.product_id: None}, synchronize_session=False)
    )
