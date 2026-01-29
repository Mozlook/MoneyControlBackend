from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas.aggregation import (
    CategoriesProductsSummaryRead,
    ImportanceSummaryRead,
)
from ..handlers import summary as summary_handler

router = APIRouter(
    prefix="/wallets/{wallet_id}/summary",
    tags=["summary"],
)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/categories-products",
    response_model=CategoriesProductsSummaryRead,
)
def summary_categories_products(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    include_empty: bool = False,
):
    return summary_handler.summary_categories_products(
        wallet_id=wallet_id,
        db=db,
        current_user=current_user,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
        include_empty=include_empty,
    )


@router.get(
    "/by-importance",
    response_model=ImportanceSummaryRead,
)
def summary_by_importance(
    wallet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
):
    return summary_handler.summary_by_importance(
        wallet_id=wallet_id,
        db=db,
        current_user=current_user,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
    )
