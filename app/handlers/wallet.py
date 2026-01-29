from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlmodel import col

from ..helpers.fx import normalize_currency
from ..helpers.users import require_user_settings
from ..helpers.wallets import ensure_wallet_member, ensure_wallet_owner
from ..models import User, Wallet, WalletUser
from ..schemas.wallet import WalletCreate, WalletRead, WalletMemberAdd, MemberRead


def _wallet_read(wallet: Wallet, role: str) -> WalletRead:
    return WalletRead(
        id=wallet.id,
        name=wallet.name,
        currency=wallet.currency,
        created_at=wallet.created_at,
        role=role,
    )


def create_wallet(
    *,
    body: WalletCreate,
    db: Session,
    current_user: User,
) -> WalletRead:
    if body.currency is not None:
        currency = normalize_currency(body.currency)
    else:
        settings = require_user_settings(current_user)
        currency = normalize_currency(settings.currency)

    wallet = Wallet(
        name=body.name,
        currency=currency,
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

    return _wallet_read(wallet, membership.role)


def list_wallets(
    *,
    db: Session,
    current_user: User,
) -> list[WalletRead]:
    memberships = (
        db.query(WalletUser)
        .options(selectinload(WalletUser.wallet))
        .filter(col(WalletUser.user_id) == current_user.id)
        .order_by(col(WalletUser.created_at))
        .all()
    )

    out: list[WalletRead] = []
    for m in memberships:
        out.append(_wallet_read(m.wallet, m.role))
    return out


def get_wallet(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
) -> WalletRead:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    wallet = membership.wallet
    return _wallet_read(wallet, membership.role)


def add_wallet_member(
    *,
    wallet_id: UUID,
    body: WalletMemberAdd,
    db: Session,
    current_user: User,
) -> MemberRead:
    _ = ensure_wallet_owner(db, wallet_id, current_user)

    # znajdź target usera
    if body.user_id is not None:
        target = db.query(User).filter(col(User.id) == body.user_id).first()
    elif body.email is not None:
        email = body.email.strip().lower()
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or email must be provided",
            )
        target = db.query(User).filter(col(User.email) == email).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or email must be provided",
        )

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    existing = (
        db.query(WalletUser)
        .filter(
            col(WalletUser.wallet_id) == wallet_id,
            col(WalletUser.user_id) == target.id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member"
        )

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


def list_wallet_members(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
) -> list[MemberRead]:
    _ = ensure_wallet_member(db, wallet_id, current_user)

    memberships = (
        db.query(WalletUser)
        .options(selectinload(WalletUser.user))
        .filter(col(WalletUser.wallet_id) == wallet_id)
        .order_by(col(WalletUser.created_at))
        .all()
    )

    out: list[MemberRead] = []
    for m in memberships:
        u = m.user
        out.append(
            MemberRead(
                user_id=u.id,
                email=u.email,
                display_name=u.display_name,
                role=m.role,
            )
        )
    return out
