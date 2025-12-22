from pydantic import BaseModel, ConfigDict


class UserSettingsUpdate(BaseModel):
    language: str | None = None
    currency: str | None = None
    billing_day: int | None = None
    timezone: str | None = None


class UserSettingsRead(BaseModel):
    language: str
    currency: str
    billing_day: int
    timezone: str

    model_config = ConfigDict(from_attributes=True)
