from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class CategoryCreate(BaseModel):
    name: str
    color: str | None = None
    icon: str | None = None


class CategoryRead(BaseModel):
    id: UUID
    name: str
    color: str | None = None
    icon: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryListItemRead(CategoryRead):
    period_sum: Decimal
