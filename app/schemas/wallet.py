from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict
from sqlmodel import SQLModel


class WalletBase(SQLModel):
    name: str


class WalletCreate(WalletBase):
    currency: str | None = None


class WalletRead(WalletBase):
    id: UUID
    currency: str
    created_at: datetime
    role: str

    model_config = ConfigDict(from_attributes=True)


class WalletMemberAdd(SQLModel):
    user_id: UUID | None = None
    email: str | None = None


class MemberRead(SQLModel):
    user_id: UUID
    email: str
    display_name: str | None
    role: str
