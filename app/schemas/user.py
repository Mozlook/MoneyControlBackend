import uuid
from datetime import datetime

from pydantic import ConfigDict, EmailStr
from sqlmodel import SQLModel


class UserBase(SQLModel):
    email: EmailStr
    display_name: str | None = None


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
