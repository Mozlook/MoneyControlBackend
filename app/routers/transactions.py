from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..handlers import transactions as transactions_handler
from ..logging_setup import setup_logger
from ..models import User
from ..schemas.transaction import TransactionCreate, TransactionRead

router = APIRouter(
    prefix="/wallets/{wallet_id}/transactions",
    tags=["transactions"],
)

logger = setup_logger()

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _clean_data(d: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in d.items() if v is not None}


@router.post("", response_model=TransactionRead, status_code=201)
def create_transaction(
    wallet_id: UUID,
    body: TransactionCreate,
    db: DB,
    current_user: CurrentUser,
    request: Request,
) -> TransactionRead:
    try:
        tx = transactions_handler.create_transaction(
            wallet_id=wallet_id,
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
                            "action": "transaction_create",
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
        "transaction created",
        extra={
            "event_type": "audit_transaction_created",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": _clean_data(
                {
                    "wallet_id": str(wallet_id),
                    "transaction_id": str(tx.id),
                    "category_id": str(body.category_id),
                    "product_id": str(body.product_id) if body.product_id else None,
                    "amount": str(body.amount),
                    "currency": body.currency,
                    "amount_base": getattr(tx, "amount_base", None),
                    "currency_base": getattr(tx, "currency_base", None),
                    "amount_original": getattr(tx, "amount_original", None),
                    "currency_original": getattr(tx, "currency_original", None),
                    "fx_rate": getattr(tx, "fx_rate", None),
                    "transaction_type": getattr(tx, "type", None),
                }
            ),
        },
    )
    return tx


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    from_date: date | None = None,
    to_date: date | None = None,
    current_period: bool = False,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
) -> list[TransactionRead]:
    return transactions_handler.list_transactions(
        wallet_id=wallet_id,
        db=db,
        current_user=current_user,
        from_date=from_date,
        to_date=to_date,
        current_period=current_period,
        category_id=category_id,
        product_id=product_id,
    )


@router.post(
    "/{transaction_id}/refund", response_model=TransactionRead, status_code=201
)
def refund_transaction(
    wallet_id: UUID,
    transaction_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
) -> TransactionRead:
    try:
        refund_tx = transactions_handler.refund_transaction(
            wallet_id=wallet_id,
            transaction_id=transaction_id,
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
                        "action": "transaction_refund",
                        "transaction_id": str(transaction_id),
                    },
                },
            )
        raise

    logger.info(
        "transaction refunded",
        extra={
            "event_type": "audit_transaction_refunded",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": _clean_data(
                {
                    "wallet_id": str(wallet_id),
                    "original_transaction_id": str(transaction_id),
                    "refund_transaction_id": str(refund_tx.id),
                    "amount_base": getattr(refund_tx, "amount_base", None),
                    "currency_base": getattr(refund_tx, "currency_base", None),
                    "amount_original": getattr(refund_tx, "amount_original", None),
                    "currency_original": getattr(refund_tx, "currency_original", None),
                    "fx_rate": getattr(refund_tx, "fx_rate", None),
                }
            ),
        },
    )
    return refund_tx


@router.delete("/{transaction_id}", status_code=204)
def soft_delete_transaction(
    wallet_id: UUID,
    transaction_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
) -> None:
    try:
        transactions_handler.soft_delete_transaction(
            wallet_id=wallet_id,
            transaction_id=transaction_id,
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
                        "action": "transaction_delete_soft",
                        "transaction_id": str(transaction_id),
                    },
                },
            )
        raise

    logger.info(
        "transaction soft deleted",
        extra={
            "event_type": "audit_transaction_deleted_soft",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "transaction_id": str(transaction_id),
            },
        },
    )
    return None


@router.get("/export", response_class=StreamingResponse)
def export_transactions(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    request: Request,
    format: str = "csv",
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
) -> StreamingResponse:
    try:
        resp = transactions_handler.export_transactions(
            wallet_id=wallet_id,
            db=db,
            current_user=current_user,
            format=format,
            current_period=current_period,
            from_date=from_date,
            to_date=to_date,
            category_id=category_id,
            product_id=product_id,
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
                            "action": "transactions_export",
                            "format": format,
                            "current_period": current_period,
                            "from_date": from_date,
                            "to_date": to_date,
                            "category_id": str(category_id) if category_id else None,
                            "product_id": str(product_id) if product_id else None,
                        }
                    ),
                },
            )
        raise

    logger.warning(
        "transactions exported",
        extra={
            "event_type": "audit_transactions_exported",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": _clean_data(
                {
                    "wallet_id": str(wallet_id),
                    "format": format,
                    "current_period": current_period,
                    "from_date": from_date,
                    "to_date": to_date,
                    "category_id": str(category_id) if category_id else None,
                    "product_id": str(product_id) if product_id else None,
                }
            ),
        },
    )
    return resp
