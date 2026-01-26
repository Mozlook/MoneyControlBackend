from pydantic import ConfigDict
from sqlmodel import SQLModel


class UserSettingsBase(SQLModel):
    language: str
    currency: str
    billing_day: int
    timezone: str


class UserSettingsUpdate(SQLModel):
    language: str | None = None
    currency: str | None = None
    billing_day: int | None = None
    timezone: str | None = None


class UserSettingsRead(UserSettingsBase):
    model_config = ConfigDict(from_attributes=True)
