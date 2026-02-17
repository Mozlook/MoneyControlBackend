from typing import Annotated
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.category import CategoryCreate, CategoryRead, CategoryReadSum
from ..handlers import categories as categories_handler
from ..logging_setup import setup_logger

router = APIRouter(
    prefix="/wallets/{wallet_id}/categories",
    tags=["categories"],
)

logger = setup_logger()

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(
    wallet_id: UUID,
    body: CategoryCreate,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        category = categories_handler.create_category(
            db=db, wallet_id=wallet_id, body=body, current_user=current_user
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
                        "action": "category_create",
                    },
                },
            )
        raise

    logger.info(
        "category created",
        extra={
            "event_type": "audit_category_created",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "category_id": str(category.id),
            },
        },
    )
    return category


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
    request: Request,
):
    try:
        categories_handler.soft_delete_category(
            wallet_id=wallet_id,
            category_id=category_id,
            db=db,
            current_user=current_user,
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
                        "category_id": str(category_id),
                        "action": "category_delete_soft",
                    },
                },
            )
        raise

    logger.info(
        "category soft deleted",
        extra={
            "event_type": "audit_category_deleted_soft",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "category_id": str(category_id),
            },
        },
    )
    return None


@router.delete("/{category_id}/hard", status_code=204)
def hard_delete_category(
    wallet_id: UUID,
    category_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        categories_handler.hard_delete_category(
            wallet_id=wallet_id,
            category_id=category_id,
            db=db,
            current_user=current_user,
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
                        "category_id": str(category_id),
                        "action": "category_delete_hard",
                    },
                },
            )
        raise

    logger.warning(
        "category hard deleted",
        extra={
            "event_type": "audit_category_deleted_hard",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "category_id": str(category_id),
            },
        },
    )
    return None


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
