from ..schemas.category import CategoryRead
from ..schemas.transaction import ProductInTransactionRead
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class RecurringTransactionCreate(BaseModel):
    category_id: UUID
    product_id: UUID | None = None
    amount_base: Decimal
    currency_base: str
    description: str | None = None
    active: bool = True


class RecurringTransactionRead(BaseModel):
    id: UUID
    wallet_id: UUID
    category: CategoryRead
    product: ProductInTransactionRead | None = None
    amount_base: Decimal
    currency_base: str
    active: bool
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    last_applied_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
