"""Logging and JSON helpers."""

from __future__ import annotations

import json
import logging
from typing import Any


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def dumps_message(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def loads_message(raw: str) -> dict[str, Any]:
    return json.loads(raw)
