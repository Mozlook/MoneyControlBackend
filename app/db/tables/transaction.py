# pyright: reportUnannotatedClassAttribute=false

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ...schemas.transaction import TransactionMoney
from ...schemas.recurring_transactions import RecurringMoney
from ._common import utcnow


class Transaction(TransactionMoney, table=True):
    __tablename__ = "transactions"

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

    category_id: uuid.UUID = Field(
        foreign_key="categories.id",
        nullable=False,
        sa_type=PGUUID(as_uuid=True),
    )

    product_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="products.id",
        sa_type=PGUUID(as_uuid=True),
    )

    type: str = Field(default="expense", nullable=False, sa_type=String)

    occurred_at: datetime = Field(nullable=False, sa_type=DateTime(timezone=True))

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    refund_of_transaction_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="transactions.id",
        sa_type=PGUUID(as_uuid=True),
    )

    deleted_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    wallet: "Wallet" = Relationship(back_populates="transactions")
    user: "User" = Relationship(back_populates="transactions")
    category: "Category" = Relationship(back_populates="transactions")
    product: Optional["Product"] = Relationship(back_populates="transactions")

    refund_of: Optional["Transaction"] = Relationship(
        back_populates="refunds",
        sa_relationship_kwargs={"remote_side": "Transaction.id"},
    )

    refunds: list["Transaction"] = Relationship(back_populates="refund_of")


class RecurringTransaction(RecurringMoney, table=True):
    __tablename__ = "recurring_transactions"

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

    category_id: uuid.UUID = Field(
        foreign_key="categories.id",
        nullable=False,
        sa_type=PGUUID(as_uuid=True),
    )

    product_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="products.id",
        sa_type=PGUUID(as_uuid=True),
    )

    active: bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    updated_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    last_applied_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )

    wallet: "Wallet" = Relationship(back_populates="recurring_transactions")
    category: "Category" = Relationship(back_populates="recurring_transactions")
    product: Optional["Product"] = Relationship(back_populates="recurring_transactions")
