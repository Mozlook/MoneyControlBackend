from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from .deps import get_db
from .routers import auth, users

app = FastAPI()

DbSession = Annotated[Session, Depends(get_db)]

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: DbSession):
    _ = db.execute(text("SELECT 1"))
    return {"db": "ok"}
