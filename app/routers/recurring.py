from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.recurring_transactions import (
    RecurringTransactionRead,
    RecurringTransactionCreate,
)
from ..schemas.transaction import TransactionRead
from ..handlers import recurring as recurring_handler
from ..logging_setup import setup_logger

router = APIRouter(
    prefix="/wallets/{wallet_id}/recurring",
    tags=["recurring"],
)

logger = setup_logger()

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _clean_data(d: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in d.items() if v is not None}


@router.post("", response_model=RecurringTransactionRead, status_code=201)
def create_recurring_transaction(
    wallet_id: UUID,
    body: RecurringTransactionCreate,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        recurring = recurring_handler.create_recurring_transaction(
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
                    "data": _clean_data(
                        {
                            "wallet_id": str(wallet_id),
                            "action": "recurring_create",
                            "category_id": str(body.category_id),
                            "product_id": (
                                str(body.product_id) if body.product_id else None
                            ),
                        }
                    ),
                },
            )
        raise

    logger.info(
        "recurring created",
        extra={
            "event_type": "audit_recurring_created",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": _clean_data(
                {
                    "wallet_id": str(wallet_id),
                    "recurring_id": str(recurring.id),
                    "category_id": str(body.category_id),
                    "product_id": str(body.product_id) if body.product_id else None,
                    # ✅ dokładna kwota (tak jak chciałeś w transactions)
                    "amount_base": str(body.amount_base),
                    "currency_base": body.currency_base,
                }
            ),
        },
    )
    return recurring


@router.get("", response_model=list[RecurringTransactionRead])
def list_recurring_transactions(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    active: bool | None = None,
):
    # Bez dodatkowego event_type (http_request z middleware wystarczy)
    return recurring_handler.list_recurring_transactions(
        wallet_id=wallet_id, db=db, current_user=current_user, active=active
    )


@router.post("/apply", response_model=list[TransactionRead])
def apply_recurring_transactions(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        created_transactions = recurring_handler.apply_recurring_transactions(
            wallet_id=wallet_id, db=db, current_user=current_user
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
                        "action": "recurring_apply",
                    },
                },
            )
        raise

    logger.info(
        "recurring applied",
        extra={
            "event_type": "audit_recurring_applied",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "created_transactions_count": len(created_transactions),
            },
        },
    )
    return created_transactions


@router.put("/{recurring_id}", response_model=RecurringTransactionRead)
def update_recurring_transaction(
    wallet_id: UUID,
    recurring_id: UUID,
    body: RecurringTransactionCreate,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        recurring = recurring_handler.update_recurring_transaction(
            wallet_id=wallet_id,
            recurring_id=recurring_id,
            body=body,
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
                    "data": _clean_data(
                        {
                            "wallet_id": str(wallet_id),
                            "recurring_id": str(recurring_id),
                            "action": "recurring_update",
                            "category_id": str(body.category_id),
                            "product_id": (
                                str(body.product_id) if body.product_id else None
                            ),
                        }
                    ),
                },
            )
        raise

    logger.info(
        "recurring updated",
        extra={
            "event_type": "audit_recurring_updated",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": _clean_data(
                {
                    "wallet_id": str(wallet_id),
                    "recurring_id": str(recurring_id),
                    "category_id": str(body.category_id),
                    "product_id": str(body.product_id) if body.product_id else None,
                    "amount_base": str(body.amount_base),
                    "currency_base": body.currency_base,
                }
            ),
        },
    )
    return recurring


@router.delete("/{recurring_id}", status_code=204)
def deactivate_recurring_transaction(
    wallet_id: UUID,
    recurring_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        recurring_handler.deactivate_recurring_transaction(
            wallet_id=wallet_id,
            recurring_id=recurring_id,
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
                        "recurring_id": str(recurring_id),
                        "action": "recurring_deactivate",
                    },
                },
            )
        raise

    logger.info(
        "recurring deactivated",
        extra={
            "event_type": "audit_recurring_deactivated",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "recurring_id": str(recurring_id),
            },
        },
    )
    return None


@router.put("/{recurring_id}/activate", status_code=204)
def activate_recurring_transaction(
    wallet_id: UUID,
    recurring_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
):
    try:
        recurring_handler.activate_recurring_transaction(
            wallet_id=wallet_id,
            recurring_id=recurring_id,
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
                        "recurring_id": str(recurring_id),
                        "action": "recurring_activate",
                    },
                },
            )
        raise

    logger.info(
        "recurring activated",
        extra={
            "event_type": "audit_recurring_activated",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "recurring_id": str(recurring_id),
            },
        },
    )
    return None
