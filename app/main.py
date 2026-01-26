from contextlib import asynccontextmanager

from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session, configure_mappers

from .deps import get_db
from .routers import (
    auth,
    users,
    wallet,
    categories,
    products,
    transactions,
    recurring,
    settings,
    summary,
    history,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app import models

    configure_mappers()
    yield


app = FastAPI(lifespan=lifespan)

DbSession = Annotated[Session, Depends(get_db)]

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(wallet.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(transactions.router)
app.include_router(recurring.router)
app.include_router(settings.router)
app.include_router(summary.router)
app.include_router(history.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: DbSession):
    _ = db.execute(text("SELECT 1"))
    return {"db": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
