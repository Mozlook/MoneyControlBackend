from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WalletCreate(BaseModel):
    name: str
    currency: str | None


class WalletRead(BaseModel):
    id: UUID
    name: str
    currency: str
    created_at: datetime
    role: str

    model_config = ConfigDict(from_attributes=True)
