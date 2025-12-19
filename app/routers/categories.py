from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User, Category
from ..schemas.category import CategoryCreate, CategoryRead
from ..helpers.helpers import ensure_wallet_member

router = APIRouter(
    prefix="/wallets/{wallet_id}/categories",
    tags=["categories"],
)


@router.post("/", response_model=CategoryRead, status_code=201)
def create_category(
    wallet_id: UUID,
    body: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    existing = (
        db.query(Category)
        .filter(
            Category.wallet_id == wallet_id,
            Category.name == body.name,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="Category with this name already exists in this wallet",
        )

    category = Category(
        wallet_id=wallet_id,
        name=body.name,
        color=body.color,
        icon=body.icon,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return CategoryRead.model_validate(category)
