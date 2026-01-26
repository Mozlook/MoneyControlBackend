from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict
from sqlmodel import SQLModel, Field
from sqlalchemy import Numeric, String

from .category import CategoryRead
from .product import ProductPublic


class ProductInTransactionRead(ProductPublic):
    pass


class TransactionCreate(SQLModel):
    category_id: UUID
    product_id: UUID | None = None
    amount: Decimal
    currency: str


class TransactionMoney(SQLModel):
    amount_base: Decimal = Field(sa_type=Numeric(12, 2))
    currency_base: str = Field(sa_type=String(3))

    amount_original: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    currency_original: str | None = Field(default=None, sa_type=String(3))
    fx_rate: Decimal | None = Field(default=None, sa_type=Numeric(18, 6))


class TransactionRead(TransactionMoney):
    id: UUID
    wallet_id: UUID
    user_id: UUID
    refund_of_transaction_id: UUID | None = None
    type: str
    occurred_at: datetime
    created_at: datetime
    category: CategoryRead
    product: ProductInTransactionRead | None = None

    model_config = ConfigDict(from_attributes=True)
