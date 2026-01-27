from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas.aggregation import LastPeriodsHistoryRead
from ..handlers import history as history_handler

router = APIRouter(
    prefix="/wallets/{wallet_id}/history",
    tags=["history"],
)


@router.get(
    "/last-periods",
    response_model=LastPeriodsHistoryRead,
    status_code=200,
)
def history_last_periods(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    periods: int = 6,
):
    return history_handler.history_last_periods(
        wallet_id=wallet_id, db=db, current_user=current_user, periods=periods
    )
