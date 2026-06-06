#!/usr/bin/env python3
"""Генерация JWT для локального теста (воркер + контроллер, RU и EN)."""

from __future__ import annotations

import os
import sys

from _bootstrap import DEFAULT_PROJECT_ID, USER_EN, USER_RU

from nexusbridgehub.auth import AuthManager
from nexusbridgehub.protocol import Role


def _require_secret() -> str:
    secret = os.getenv("NEXUSBRIDGEHUB_JWT_SECRET", "")
    if len(secret) < 32:
        print(
            "Задай NEXUSBRIDGEHUB_JWT_SECRET (минимум 32 символа).\n"
            "PowerShell: $env:NEXUSBRIDGEHUB_JWT_SECRET=\"твой_длинный_секрет_32plus\"\n"
            "bash:       export NEXUSBRIDGEHUB_JWT_SECRET=\"твой_длинный_секрет_32plus\"",
            file=sys.stderr,
        )
        sys.exit(1)
    return secret


def main() -> None:
    auth = AuthManager(_require_secret())
    project = DEFAULT_PROJECT_ID

    pairs = [
        ("RU", USER_RU),
        ("EN", USER_EN),
    ]

    print(f"project_id = {project}\n")
    for label, user_id in pairs:
        worker = auth.create_token(role=Role.WORKER, project_id=project, user_id=user_id)
        controller = auth.create_token(role=Role.CONTROLLER, project_id=project, user_id=user_id)
        print(f"--- {label} (user_id={user_id}) ---")
        print(f"WORKER_TOKEN_{label}={worker}")
        print(f"CONTROLLER_TOKEN_{label}={controller}\n")

    print("Скопируй токены в переменные окружения перед запуском worker_*.py и controller_*.py.")


if __name__ == "__main__":
    main()
