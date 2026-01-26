from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict
from sqlmodel import SQLModel, Field
from sqlalchemy import Numeric, String

from .category import CategoryRead
from .transaction import ProductInTransactionRead


class RecurringMoney(SQLModel):
    amount_base: Decimal = Field(sa_type=Numeric(12, 2))
    currency_base: str = Field(sa_type=String(3))
    description: str | None = None


class RecurringTransactionCreate(RecurringMoney):
    category_id: UUID
    product_id: UUID | None = None


class RecurringTransactionRead(RecurringMoney):
    id: UUID
    wallet_id: UUID
    category: CategoryRead
    product: ProductInTransactionRead | None = None
    active: bool
    created_at: datetime
    updated_at: datetime
    last_applied_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
