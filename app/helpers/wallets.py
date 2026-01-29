from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models import WalletUser, User
from sqlmodel import col


def ensure_wallet_member(
    db: Session, wallet_id: UUID, current_user: User
) -> WalletUser:
    membership = (
        db.query(WalletUser)
        .filter(
            col(WalletUser.wallet_id) == wallet_id,
            col(WalletUser.user_id) == current_user.id,
        )
        .first()
    )

    if membership is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return membership


def ensure_wallet_owner(db: Session, wallet_id: UUID, current_user: User) -> WalletUser:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    if membership.role != "owner":
        raise HTTPException(
            status_code=403, detail="Only owner can perform this action"
        )

    return membership
