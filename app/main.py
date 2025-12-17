from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from .deps import get_db

app = FastAPI()

DbSession = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: DbSession):
    _ = db.execute(text("SELECT 1"))
    return {"db": "ok"}
