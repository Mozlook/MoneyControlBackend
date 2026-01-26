from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict
from sqlmodel import SQLModel, Field
from sqlalchemy import Enum as SAEnum

from ..domain.enums import ProductImportance
from .category import CategoryRead


class ProductBase(SQLModel):
    name: str
    importance: ProductImportance = Field(
        sa_type=SAEnum(ProductImportance, name="product_importance_enum")
    )


class ProductCreate(ProductBase):
    category_id: UUID


class ProductPublic(ProductBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class ProductRead(ProductPublic):
    created_at: datetime
    category: CategoryRead


class ProductReadSum(ProductRead):
    period_sum: Decimal
