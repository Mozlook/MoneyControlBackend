from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User, Product, Category
from ..schemas.product import ProductCreate, ProductRead
from ..helpers.wallets import ensure_wallet_member

router = APIRouter(
    prefix="/wallets/{wallet_id}/products",
    tags=["products"],
)


@router.post("/", response_model=ProductRead, status_code=201)
def create_product(
    wallet_id: UUID,
    body: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    category = (
        db.query(Category)
        .filter(
            Category.id == body.category_id,
            Category.wallet_id == wallet_id,
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        wallet_id=wallet_id,
        category_id=body.category_id,
        name=body.name,
        importance=body.importance,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return ProductRead.model_validate(product)


@router.get("/", response_model=list[ProductRead], status_code=200)
def list_products(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    products = (
        db.query(Product)
        .filter(
            Product.wallet_id == wallet_id,
            Product.deleted_at.is_(None),
        )
        .order_by(Product.created_at)
        .all()
    )
    return [ProductRead.model_validate(p) for p in products]
