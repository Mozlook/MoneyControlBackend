from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlmodel import col

from ..models import Category


def get_category(db: Session, *, wallet_id: UUID, category_id: UUID) -> Category | None:
    return (
        db.query(Category)
        .filter(col(Category.wallet_id) == wallet_id, col(Category.id) == category_id)
        .first()
    )


def get_category_or_404(
    db: Session,
    *,
    wallet_id: UUID,
    category_id: UUID,
    require_not_deleted: bool | None = None,
) -> Category:
    cat = get_category(db, wallet_id=wallet_id, category_id=category_id)

    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if require_not_deleted is True and cat.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if require_not_deleted is False and cat.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="soft delete category first"
        )

    return cat


def soft_delete_now(cat: Category) -> None:
    cat.deleted_at = datetime.now(timezone.utc)


def ensure_category_name_unique(db: Session, *, wallet_id: UUID, name: str) -> None:
    exists = (
        db.query(col(Category.id))
        .filter(col(Category.wallet_id) == wallet_id, col(Category.name) == name)
        .first()
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists in this wallet",
        )
