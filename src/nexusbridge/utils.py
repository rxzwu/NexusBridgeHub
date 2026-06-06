"""Logging and JSON helpers."""

from __future__ import annotations

import json
import logging
import os
from typing import Any


def setup_logging(level: int | None = None) -> None:
    if level is None:
        env = os.getenv("NEXUSBRIDGE_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, env, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


def format_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def dumps_message(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def loads_message(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("message must be a JSON object")
    return data
