from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..handlers import wallet as wallets_handler
from ..models import User
from ..schemas.wallet import WalletCreate, WalletRead, WalletMemberAdd, MemberRead
from ..logging_setup import setup_logger

router = APIRouter(prefix="/wallets", tags=["wallets"])
logger = setup_logger()

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=WalletRead, status_code=201)
def create_wallet(
    body: WalletCreate,
    db: DB,
    current_user: CurrentUser,
    request: Request,
) -> WalletRead:
    wallet = wallets_handler.create_wallet(body=body, db=db, current_user=current_user)

    logger.info(
        "wallet created",
        extra={
            "event_type": "audit_wallet_created",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet.id),
                "currency": wallet.currency,
            },
        },
    )
    return wallet


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
    request: Request,
) -> MemberRead:
    try:
        member = wallets_handler.add_wallet_member(
            wallet_id=wallet_id, body=body, db=db, current_user=current_user
        )

    except HTTPException as exc:
        if exc.status_code == 403:

            target_email_domain = None
            if body.email and "@" in body.email:
                target_email_domain = body.email.split("@", 1)[1].lower()

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
                        "action": "wallet_add_member",
                        "target_user_id": str(body.user_id) if body.user_id else None,
                        "target_email_domain": target_email_domain,
                    },
                },
            )
        raise

    target_email_domain: str | None = None
    if body.email and "@" in body.email:
        target_email_domain = body.email.split("@", 1)[1].lower()

    logger.info(
        "wallet member added",
        extra={
            "event_type": "audit_wallet_member_added",
            "user_id": str(current_user.id),
            "src_ip": request.client.host if request.client else None,
            "user_agent": (request.headers.get("user-agent") or "")[:256],
            "data": {
                "wallet_id": str(wallet_id),
                "member_user_id": str(member.user_id),
                "role": member.role,
                "target_email_domain": target_email_domain,
            },
        },
    )
    return member


@router.get("/{wallet_id}/members", response_model=list[MemberRead])
def list_wallet_members(
    wallet_id: UUID, db: DB, current_user: CurrentUser
) -> list[MemberRead]:
    return wallets_handler.list_wallet_members(
        wallet_id=wallet_id, db=db, current_user=current_user
    )
