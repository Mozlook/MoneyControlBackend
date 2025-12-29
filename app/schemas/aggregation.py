from datetime import datetime
from .transaction import ProductInTransactionRead
from .category import CategoryRead
from decimal import Decimal
from pydantic import BaseModel


class ProductWithSumRead(BaseModel):
    product: ProductInTransactionRead
    product_sum: Decimal


class CategoriesWithProductsSummaryRead(BaseModel):
    category: CategoryRead
    category_sum: Decimal
    no_product_sum: Decimal
    products: list[ProductWithSumRead]


class CategoriesProductsSummaryRead(BaseModel):
    currency: str
    period_start: datetime
    period_end: datetime
    total: Decimal
    categories: list[CategoriesWithProductsSummaryRead]


class ImportanceSummaryRead(BaseModel):
    currency: str
    period_start: datetime
    period_end: datetime
    total: Decimal
    necessary: Decimal
    important: Decimal
    unnecessary: Decimal
    unassigned: Decimal


class PeriodTotalRead(BaseModel):
    period_start: datetime
    period_end: datetime
    total: Decimal


class LastPeriodsHistoryRead(BaseModel):
    currency: str
    periods: list[PeriodTotalRead]
