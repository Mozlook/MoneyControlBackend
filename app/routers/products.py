from typing import Annotated
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.product import ProductCreate, ProductRead, ProductReadSum
from ..handlers import products as products_handler

router = APIRouter(
    prefix="/wallets/{wallet_id}/products",
    tags=["products"],
)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    wallet_id: UUID, body: ProductCreate, db: DB, current_user: CurrentUser
):
    return products_handler.create_product(
        wallet_id=wallet_id, body=body, db=db, current_user=current_user
    )


@router.get("", response_model=list[ProductRead], status_code=200)
def list_products(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    category_id: UUID | None = None,
    deleted: bool = False,
):
    return products_handler.list_products(
        wallet_id=wallet_id,
        db=db,
        current_user=current_user,
        category_id=category_id,
        deleted=deleted,
    )


@router.delete("/{product_id}", status_code=204)
def soft_delete_product(
    wallet_id: UUID,
    product_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    products_handler.soft_delete_product(
        wallet_id=wallet_id, product_id=product_id, db=db, current_user=current_user
    )


@router.delete("/{product_id}/hard", status_code=204)
def hard_delete_product(
    wallet_id: UUID,
    product_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    products_handler.hard_delete_product(
        wallet_id=wallet_id, product_id=product_id, db=db, current_user=current_user
    )


@router.get("/with-sum", response_model=list[ProductReadSum], status_code=200)
def list_products_with_sum(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    category_id: UUID | None = None,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[ProductReadSum]:
    return products_handler.list_products_with_sum(
        wallet_id=wallet_id,
        db=db,
        current_user=current_user,
        category_id=category_id,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
    )
