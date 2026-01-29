from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..helpers.categories import get_category_or_404
from ..helpers.products import get_product_or_404
from ..models import Category, Product


def validate_category_and_optional_product(
    db: Session,
    *,
    wallet_id: UUID,
    category_id: UUID,
    product_id: UUID | None,
) -> tuple[Category, Product | None]:
    category = get_category_or_404(
        db=db, wallet_id=wallet_id, category_id=category_id, require_not_deleted=True
    )

    if product_id is None:
        return category, None

    product = get_product_or_404(
        db=db, wallet_id=wallet_id, product_id=product_id, require_not_deleted=True
    )

    if product.category_id != category.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="product does not belong to this category",
        )

    return category, product
