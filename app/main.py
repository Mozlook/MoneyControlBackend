from __future__ import annotations

import time
from .logging_setup import setup_logger, request_id_ctx, new_request_id
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, HTTPException
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

logger = setup_logger()


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or new_request_id()
    token = request_id_ctx.set(rid)

    start = time.perf_counter()
    response = None
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    except Exception as exc:
        if not isinstance(exc, HTTPException):
            logger.error(
                "unhandled exception",
                extra={
                    "event_type": "unhandled_exception",
                    "error_type": type(exc).__name__,
                    "src_ip": request.client.host if request.client else None,
                    "method": request.method,
                    "path": f"{request.scope.get('root_path','')}{request.url.path}",
                    "user_agent": (request.headers.get("user-agent") or "")[:256],
                },
                exc_info=True,
            )
        raise

    finally:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        user_id = getattr(request.state, "user_id", None)

        logger.info(
            "request",
            extra={
                "event_type": "http_request",
                "user_id": user_id,
                "src_ip": request.client.host if request.client else None,
                "method": request.method,
                "path": f"{request.scope.get('root_path','')}{request.url.path}",
                "status": status_code,
                "latency_ms": latency_ms,
                "user_agent": (request.headers.get("user-agent") or "")[:256],
            },
        )

        if response is not None:
            response.headers["X-Request-ID"] = rid

        request_id_ctx.reset(token)


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
