from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WalletCreate(BaseModel):
    name: str
    currency: str | None = None


class WalletRead(BaseModel):
    id: UUID
    name: str
    currency: str
    created_at: datetime
    role: str

    model_config = ConfigDict(from_attributes=True)


class WalletMemberAdd(BaseModel):
    user_id: UUID | None = None
    email: str | None = None


class MemberRead(BaseModel):
    user_id: UUID
    email: str
    display_name: str | None
    role: str
