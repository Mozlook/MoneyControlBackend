# pyright: reportUnannotatedClassAttribute=false

import uuid
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from ...schemas.category import CategoryBase
from ...schemas.product import ProductBase
from ._common import utcnow


class Category(CategoryBase, table=True):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("wallet_id", "name", name="uix_category_wallet_name"),
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

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    deleted_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    wallet: "Wallet" = Relationship(back_populates="categories")

    products: list["Product"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    transactions: list["Transaction"] = Relationship(back_populates="category")
    recurring_transactions: list["RecurringTransaction"] = Relationship(
        back_populates="category"
    )


class Product(ProductBase, table=True):
    __tablename__ = "products"

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

    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
    )

    deleted_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    wallet: "Wallet" = Relationship(back_populates="products")
    category: "Category" = Relationship(back_populates="products")

    transactions: list["Transaction"] = Relationship(back_populates="product")
    recurring_transactions: list["RecurringTransaction"] = Relationship(
        back_populates="product"
    )
