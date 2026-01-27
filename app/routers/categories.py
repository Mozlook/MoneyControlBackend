from typing import Annotated
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.category import CategoryCreate, CategoryRead, CategoryReadSum
from ..handlers import categories as categories_handler

router = APIRouter(
    prefix="/wallets/{wallet_id}/categories",
    tags=["categories"],
)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(
    wallet_id: UUID,
    body: CategoryCreate,
    db: DB,
    current_user: CurrentUser,
):
    return categories_handler.create_category(
        db=db, wallet_id=wallet_id, body=body, current_user=current_user
    )


@router.get("", response_model=list[CategoryRead])
def list_categories(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    deleted: bool = False,
):
    return categories_handler.list_categories(
        wallet_id=wallet_id, db=db, current_user=current_user, deleted=deleted
    )


@router.delete("/{category_id}", status_code=204)
def soft_delete_category(
    wallet_id: UUID,
    category_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    return categories_handler.soft_delete_category(
        wallet_id=wallet_id, category_id=category_id, db=db, current_user=current_user
    )


@router.delete("/{category_id}/hard", status_code=204)
def hard_delete_category(
    wallet_id: UUID,
    category_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    return categories_handler.hard_delete_category(
        wallet_id=wallet_id, category_id=category_id, db=db, current_user=current_user
    )


@router.get("/with-sum", response_model=list[CategoryReadSum])
def list_categories_with_sum(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    include_empty: bool = True,
) -> list[CategoryReadSum]:
    return categories_handler.list_categories_with_sum(
        wallet_id=wallet_id,
        db=db,
        current_user=current_user,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
        include_empty=include_empty,
    )
