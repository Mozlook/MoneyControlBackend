from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from ..schemas.category import CategoryRead
from ..models import ProductImportance


class ProductCreate(BaseModel):
    name: str
    category_id: UUID
    importance: ProductImportance


class ProductRead(BaseModel):
    id: UUID
    name: str
    importance: ProductImportance
    created_at: datetime
    category: CategoryRead

    model_config = ConfigDict(from_attributes=True)


class ProductReadSum(ProductRead):
    period_sum: Decimal
