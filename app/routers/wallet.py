from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User, Wallet, WalletUser
from ..schemas.wallet import WalletCreate, WalletRead, WalletMemberAdd, MemberRead
from ..helpers.wallets import ensure_wallet_member, ensure_wallet_owner

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

    wallet = Wallet(
        name=body.name,
        currency=currency.upper(),
        owner_id=current_user.id,
    )
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
    # UŻYCIE HELPERA
    membership = ensure_wallet_member(db, wallet_id, current_user)
    wallet = membership.wallet

    return WalletRead(
        id=wallet.id,
        name=wallet.name,
        currency=wallet.currency,
        created_at=wallet.created_at,
        role=membership.role,
    )


@router.post("/{wallet_id}/members", response_model=MemberRead, status_code=201)
def add_wallet_member(
    wallet_id: UUID,
    body: WalletMemberAdd,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_owner(db, wallet_id, current_user)

    if body.user_id:
        target = db.query(User).filter(User.id == body.user_id).first()
    elif body.email:
        target = db.query(User).filter(User.email == body.email).first()
    else:
        raise HTTPException(
            status_code=400,
            detail="Either user_id or email must be provided",
        )

    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(WalletUser)
        .filter(
            WalletUser.wallet_id == wallet_id,
            WalletUser.user_id == target.id,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(status_code=400, detail="User is already a member")

    new_membership = WalletUser(
        wallet_id=wallet_id,
        user_id=target.id,
        role="editor",
    )

    db.add(new_membership)
    db.commit()

    return MemberRead(
        user_id=target.id,
        email=target.email,
        display_name=target.display_name,
        role=new_membership.role,
    )


@router.get("/{wallet_id}/members", response_model=list[MemberRead], status_code=200)
def list_wallet_members(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    _ = ensure_wallet_member(db, wallet_id, current_user)

    memberships = db.query(WalletUser).filter(WalletUser.wallet_id == wallet_id).all()

    result: list[MemberRead] = []

    for m in memberships:
        user = m.user

        item = MemberRead(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=m.role,
        )
        result.append(item)

    return result
