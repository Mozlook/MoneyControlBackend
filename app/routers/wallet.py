from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..handlers import wallet as wallets_handler
from ..models import User
from ..schemas.wallet import WalletCreate, WalletRead, WalletMemberAdd, MemberRead

router = APIRouter(prefix="/wallets", tags=["wallets"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=WalletRead, status_code=201)
def create_wallet(body: WalletCreate, db: DB, current_user: CurrentUser) -> WalletRead:
    return wallets_handler.create_wallet(body=body, db=db, current_user=current_user)


@router.get("", response_model=list[WalletRead])
def list_wallets(db: DB, current_user: CurrentUser) -> list[WalletRead]:
    return wallets_handler.list_wallets(db=db, current_user=current_user)


@router.get("/{wallet_id}", response_model=WalletRead)
def get_wallet(wallet_id: UUID, db: DB, current_user: CurrentUser) -> WalletRead:
    return wallets_handler.get_wallet(
        wallet_id=wallet_id, db=db, current_user=current_user
    )


@router.post("/{wallet_id}/members", response_model=MemberRead, status_code=201)
def add_wallet_member(
    wallet_id: UUID,
    body: WalletMemberAdd,
    db: DB,
    current_user: CurrentUser,
) -> MemberRead:
    return wallets_handler.add_wallet_member(
        wallet_id=wallet_id, body=body, db=db, current_user=current_user
    )


@router.get("/{wallet_id}/members", response_model=list[MemberRead])
def list_wallet_members(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> list[MemberRead]:
    return wallets_handler.list_wallet_members(
        wallet_id=wallet_id, db=db, current_user=current_user
    )
