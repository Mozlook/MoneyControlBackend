# pyright: reportUnannotatedClassAttribute=false
import uuid
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ...schemas.wallet import WalletBase
from ._common import utcnow


class Wallet(WalletBase, table=True):
    __tablename__ = "wallets"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_type=PGUUID(as_uuid=True),
    )

    currency: str = Field(nullable=False, sa_type=String(3))

    owner_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        sa_type=PGUUID(as_uuid=True),
    )

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    owner: "User" = Relationship(back_populates="owned_wallets")

    memberships: list["WalletUser"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    categories: list["Category"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    products: list["Product"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    transactions: list["Transaction"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    recurring_transactions: list["RecurringTransaction"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class WalletUser(SQLModel, table=True):
    __tablename__ = "wallet_users"
    __table_args__ = (
        UniqueConstraint("wallet_id", "user_id", name="uix_wallet_user_unique"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_type=PGUUID(as_uuid=True),
    )

    wallet_id: uuid.UUID = Field(
        foreign_key="wallets.id",
        nullable=False,
        sa_type=PGUUID(as_uuid=True),
    )

    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        sa_type=PGUUID(as_uuid=True),
    )

    role: str = Field(default="editor", nullable=False, sa_type=String)

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    wallet: "Wallet" = Relationship(back_populates="memberships")
    user: "User" = Relationship(back_populates="wallet_memberships")
