from fastapi import APIRouter, Depends
from typing import Annotated

from ..schemas.user import UserRead
from ..models import User
from ..deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
