from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas.recurring_transactions import (
    RecurringTransactionRead,
    RecurringTransactionCreate,
)
from ..schemas.transaction import TransactionRead
from ..handlers import recurring as recurring_handler

router = APIRouter(
    prefix="/wallets/{wallet_id}/recurring",
    tags=["recurring"],
)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=RecurringTransactionRead, status_code=201)
def create_recurring_transaction(
    wallet_id: UUID,
    body: RecurringTransactionCreate,
    db: DB,
    current_user: CurrentUser,
):
    return recurring_handler.create_recurring_transaction(
        wallet_id=wallet_id, body=body, db=db, current_user=current_user
    )


@router.get("", response_model=list[RecurringTransactionRead])
def list_recurring_transactions(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    active: bool | None = None,
):
    return recurring_handler.list_recurring_transactions(
        wallet_id=wallet_id, db=db, current_user=current_user, active=active
    )


@router.post("/apply", response_model=list[TransactionRead])
def apply_recurring_transactions(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    return recurring_handler.apply_recurring_transactions(
        wallet_id=wallet_id, db=db, current_user=current_user
    )


@router.put("/{recurring_id}", response_model=RecurringTransactionRead)
def update_recurring_transaction(
    wallet_id: UUID,
    recurring_id: UUID,
    body: RecurringTransactionCreate,
    db: DB,
    current_user: CurrentUser,
):
    return recurring_handler.update_recurring_transaction(
        wallet_id=wallet_id,
        recurring_id=recurring_id,
        body=body,
        db=db,
        current_user=current_user,
    )


@router.delete("/{recurring_id}", status_code=204)
def deactivate_recurring_transaction(
    wallet_id: UUID,
    recurring_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    recurring_handler.deactivate_recurring_transaction(
        wallet_id=wallet_id, recurring_id=recurring_id, db=db, current_user=current_user
    )


@router.put("/{recurring_id}/activate", status_code=204)
def activate_recurring_transaction(
    wallet_id: UUID,
    recurring_id: UUID,
    db: DB,
    current_user: CurrentUser,
):
    recurring_handler.activate_recurring_transaction(
        wallet_id=wallet_id, recurring_id=recurring_id, db=db, current_user=current_user
    )
