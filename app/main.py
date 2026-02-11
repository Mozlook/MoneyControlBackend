from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

ROOT_PATH = os.getenv("ROOT_PATH", "").rstrip("/")

CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app import models

    configure_mappers()
    yield


app = FastAPI(
    lifespan=lifespan,
    root_path=ROOT_PATH,
)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


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


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}


@app.get("/db-check", include_in_schema=False)
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
