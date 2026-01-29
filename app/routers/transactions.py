from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID

from ..deps import get_current_user, get_db
from ..handlers import transactions as transactions_handler
from ..models import User
from ..schemas.transaction import TransactionCreate, TransactionRead

router = APIRouter(
    prefix="/wallets/{wallet_id}/transactions",
    tags=["transactions"],
)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=TransactionRead, status_code=201)
def create_transaction(
    wallet_id: UUID,
    body: TransactionCreate,
    db: DB,
    current_user: CurrentUser,
) -> TransactionRead:
    return transactions_handler.create_transaction(
        wallet_id=wallet_id,
        body=body,
        db=db,
        current_user=current_user,
    )


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
) -> TransactionRead:
    return transactions_handler.refund_transaction(
        wallet_id=wallet_id,
        transaction_id=transaction_id,
        db=db,
        current_user=current_user,
    )


@router.delete("/{transaction_id}", status_code=204)
def soft_delete_transaction(
    wallet_id: UUID,
    transaction_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> None:
    transactions_handler.soft_delete_transaction(
        wallet_id=wallet_id,
        transaction_id=transaction_id,
        db=db,
        current_user=current_user,
    )


@router.get("/export", response_class=StreamingResponse)
def export_transactions(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    format: str = "csv",
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    category_id: UUID | None = None,
    product_id: UUID | None = None,
) -> StreamingResponse:
    return transactions_handler.export_transactions(
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
