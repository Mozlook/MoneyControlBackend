# pyright: reportUnannotatedClassAttribute=false
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ...schemas.user import UserBase
from ...schemas.user_settings import UserSettingsBase
from ._common import utcnow


class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_type=PGUUID(as_uuid=True),
    )

    email: str = Field(
        index=True,
        unique=True,
        nullable=False,
        sa_type=String,
    )

    display_name: str | None = Field(default=None, sa_type=String)

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    owned_wallets: list["Wallet"] = Relationship(back_populates="owner")
    wallet_memberships: list["WalletUser"] = Relationship(back_populates="user")

    user_settings: Optional["UserSettings"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False},
    )

    oauth_accounts: list["UserOauth"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    transactions: list["Transaction"] = Relationship(back_populates="user")


class UserSettings(UserSettingsBase, table=True):
    __tablename__ = "user_settings"

    id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="users.id",
        sa_type=PGUUID(as_uuid=True),
    )

    user: "User" = Relationship(back_populates="user_settings")


class UserOauth(SQLModel, table=True):
    __tablename__ = "user_oauth"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_type=PGUUID(as_uuid=True),
    )

    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        nullable=False,
        sa_type=PGUUID(as_uuid=True),
    )

    provider: str = Field(nullable=False, sa_type=String)
    provider_sub: str = Field(nullable=False, unique=True, sa_type=String)

    refresh_token: str | None = Field(default=None, sa_type=Text)

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    updated_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    user: "User" = Relationship(back_populates="oauth_accounts")
