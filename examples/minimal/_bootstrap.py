"""Подключение nexusbridgehub из исходников репозитория (без pip install)."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Общие константы для минимального демо
DEFAULT_SERVER_URL = os.getenv("NEXUSBRIDGEHUB_SERVER_URL", "ws://127.0.0.1:8765")
DEFAULT_PROJECT_ID = os.getenv("NEXUSBRIDGEHUB_PROJECT_ID", "demo_project")
USER_RU = os.getenv("NEXUSBRIDGEHUB_USER_RU", "user-ru")
USER_EN = os.getenv("NEXUSBRIDGEHUB_USER_EN", "user-en")
