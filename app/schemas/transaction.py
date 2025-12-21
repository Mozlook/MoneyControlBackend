from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .category import CategoryRead
from ..models import ProductImportance


class ProductInTransactionRead(BaseModel):
    id: UUID
    name: str
    importance: ProductImportance

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    category_id: UUID
    product_id: UUID | None = None
    amount_base: Decimal
    currency_base: str
    amount_original: Decimal | None = None
    currency_original: str | None = None
    fx_rate: Decimal | None = None
    occurred_at: datetime


class TransactionRead(BaseModel):
    id: UUID
    wallet_id: UUID
    user_id: UUID
    refund_of_transaction_id: UUID | None = None
    type: str
    amount_base: Decimal
    currency_base: str
    amount_original: Decimal | None = None
    currency_original: str | None = None
    fx_rate: Decimal | None = None
    occurred_at: datetime
    created_at: datetime
    category: CategoryRead
    product: ProductInTransactionRead | None = None

    model_config = ConfigDict(from_attributes=True)
