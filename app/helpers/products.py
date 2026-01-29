from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlmodel import col

from ..models import Product


def get_product(
    db: Session,
    *,
    wallet_id: UUID,
    product_id: UUID,
) -> Product | None:
    return (
        db.query(Product)
        .filter(col(Product.wallet_id) == wallet_id, col(Product.id) == product_id)
        .first()
    )


def get_product_or_404(
    db: Session,
    *,
    wallet_id: UUID,
    product_id: UUID,
    require_not_deleted: bool | None = None,
) -> Product:
    product = get_product(db, wallet_id=wallet_id, product_id=product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    if require_not_deleted is True and product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    if require_not_deleted is False and product.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="soft delete product first"
        )

    return product


def soft_delete_now(product: Product) -> None:
    product.deleted_at = datetime.now(timezone.utc)
