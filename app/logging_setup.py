from __future__ import annotations

import json
import logging
import os
import socket
import time
import traceback
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from typing import override

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def _utc_ts(created: float) -> str:
    """ISO8601 UTC z milisekundami, np. 2026-02-12T12:01:02.123Z"""
    sec = int(created)
    ms = int((created - sec) * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(sec)) + f".{ms:03d}Z"


def new_request_id() -> str:
    return str(uuid.uuid4())


class JsonLineFormatter(logging.Formatter):
    app_name: str
    host: str
    include_stacktrace: bool
    allowed_extra_keys: set[str]

    def __init__(self) -> None:
        super().__init__()
        self.app_name = os.getenv("APP_NAME", "MoneyControl")
        self.host = socket.gethostname()
        self.include_stacktrace = os.getenv("LOG_INCLUDE_STACKTRACE", "0") == "1"

        self.allowed_extra_keys = {
            "event_type",
            "src_ip",
            "user_id",
            "method",
            "path",
            "status",
            "latency_ms",
            "user_agent",
            "error_type",
            "data",
        }

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": _utc_ts(record.created),
            "app": self.app_name,
            "host": self.host,
            "level": record.levelname,
            "event_type": getattr(record, "event_type", "log"),
            "request_id": request_id_ctx.get(),
            "msg": record.getMessage(),
        }

        for key in self.allowed_extra_keys:
            value = getattr(record, key, None)
            if value is None:
                continue

            if key == "data":
                if isinstance(value, dict) and value:
                    safe_data: dict[str, object] = {str(k): v for k, v in value.items()}
                    payload["data"] = safe_data
                continue

            payload[key] = value

        exc_info = record.exc_info
        if exc_info:
            exc_type, exc_val, exc_tb = exc_info
            if exc_type is not None:
                _ = payload.setdefault(
                    "error_type", getattr(exc_type, "__name__", "Exception")
                )
            if exc_val is not None:
                payload["error_msg"] = str(exc_val)

            if self.include_stacktrace and exc_type and exc_val and exc_tb:
                payload["traceback"] = "".join(
                    traceback.format_exception(exc_type, exc_val, exc_tb)
                )

        return json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), default=str
        )


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("moneycontrol")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = JsonLineFormatter()

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    log_path = os.getenv("LOG_PATH")
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fh = RotatingFileHandler(
            log_path,
            maxBytes=int(os.getenv("LOG_MAX_BYTES", "10000000")),  # 10 MB
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
