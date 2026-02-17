from typing import Annotated
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.product import ProductCreate, ProductRead, ProductReadSum
from ..handlers import products as products_handler
from ..logging_setup import setup_logger

router = APIRouter(
    prefix="/wallets/{wallet_id}/products",
    tags=["products"],
)

logger = setup_logger()

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    wallet_id: UUID,
    body: ProductCreate,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        product = products_handler.create_product(
            wallet_id=wallet_id, body=body, db=db, current_user=current_user
        )

    except HTTPException as exc:
        if exc.status_code == 403:
            logger.warning(
                "permission denied",
                extra={
                    "event_type": "permission_denied",
                    "user_id": str(current_user.id),
                    "src_ip": request.client.host if request.client else None,
                    "user_agent": (request.headers.get("user-agent") or "")[:256],
                    "status": exc.status_code,
                    "data": {
                        "wallet_id": str(wallet_id),
                        "action": "product_create",
                        "category_id": str(body.category_id),
                        "importance": body.importance,
                    },
                },
            )
        raise

    logger.info(
        "product created",
        extra={
            "event_type": "audit_product_created",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "product_id": str(product.id),
                "category_id": str(body.category_id),
                "importance": body.importance,
            },
        },
    )
    return product


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
    request: Request,
):
    try:
        products_handler.soft_delete_product(
            wallet_id=wallet_id, product_id=product_id, db=db, current_user=current_user
        )

    except HTTPException as exc:
        if exc.status_code == 403:
            logger.warning(
                "permission denied",
                extra={
                    "event_type": "permission_denied",
                    "user_id": str(current_user.id),
                    "src_ip": request.client.host if request.client else None,
                    "user_agent": (request.headers.get("user-agent") or "")[:256],
                    "status": exc.status_code,
                    "data": {
                        "wallet_id": str(wallet_id),
                        "product_id": str(product_id),
                        "action": "product_delete_soft",
                    },
                },
            )
        raise

    logger.info(
        "product soft deleted",
        extra={
            "event_type": "audit_product_deleted_soft",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "product_id": str(product_id),
            },
        },
    )
    return None


@router.delete("/{product_id}/hard", status_code=204)
def hard_delete_product(
    wallet_id: UUID,
    product_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        products_handler.hard_delete_product(
            wallet_id=wallet_id, product_id=product_id, db=db, current_user=current_user
        )

    except HTTPException as exc:
        if exc.status_code == 403:
            logger.warning(
                "permission denied",
                extra={
                    "event_type": "permission_denied",
                    "user_id": str(current_user.id),
                    "src_ip": request.client.host if request.client else None,
                    "user_agent": (request.headers.get("user-agent") or "")[:256],
                    "status": exc.status_code,
                    "data": {
                        "wallet_id": str(wallet_id),
                        "product_id": str(product_id),
                        "action": "product_delete_hard",
                    },
                },
            )
        raise

    logger.warning(
        "product hard deleted",
        extra={
            "event_type": "audit_product_deleted_hard",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "product_id": str(product_id),
            },
        },
    )
    return None


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
