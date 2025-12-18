from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User, Wallet, WalletUser
from ..schemas.wallet import WalletCreate, WalletRead

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("/", response_model=WalletRead, status_code=201)
def create_wallet(
    body: WalletCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    currency = body.currency
    if currency is None:
        currency = current_user.user_settings.currency

    wallet = Wallet(name=body.name, currency=currency.upper(), owner_id=current_user.id)
    db.add(wallet)
    db.flush()

    membership = WalletUser(
        wallet_id=wallet.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(membership)

    db.commit()

    db.refresh(wallet)

    return WalletRead(
        id=wallet.id,
        name=wallet.name,
        currency=wallet.currency,
        created_at=wallet.created_at,
        role=membership.role,
    )


@router.get("/", response_model=list[WalletRead], status_code=200)
def list_wallets(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    memberships = (
        db.query(WalletUser)
        .filter(WalletUser.user_id == current_user.id)
        .order_by(WalletUser.created_at)
        .all()
    )

    result: list[WalletRead] = []

    for membership in memberships:
        wallet = membership.wallet
        item = WalletRead(
            id=wallet.id,
            name=wallet.name,
            currency=wallet.currency,
            created_at=wallet.created_at,
            role=membership.role,
        )
        result.append(item)

    return result


@router.get("/{wallet_id}", response_model=WalletRead, status_code=200)
def get_wallet(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    membership = (
        db.query(WalletUser)
        .filter(
            WalletUser.wallet_id == wallet_id, WalletUser.user_id == current_user.id
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet = membership.wallet

    return WalletRead(
        id=wallet.id,
        name=wallet.name,
        currency=wallet.currency,
        created_at=wallet.created_at,
        role=membership.role,
    )
