"""
Пример: интеграция воркера в свой проект.

Контроллер (бот/API) живёт на сервере; тяжёлая работа выполняется локально на машине пользователя.
Типичный сценарий:
  1. Бот генерирует pair-код: auth.create_pair_code(project_id="taskrelay", user_id=user_id)
  2. Пользователь запускает воркер с --pair-code ABCD1234
  3. Бот шлёт команды через BridgeController.invoke(...)
"""

from __future__ import annotations

import asyncio
import os
import sys

# Запуск из репозитория без pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from nexusbridgehub.client import BridgeClient
from nexusbridgehub.worker_app import WorkerApp, main_cli


def register_handlers(bridge: BridgeClient) -> None:
    """Регистрация функций, доступных удалённому контроллеру (боту)."""

    async def run_task(job_id: str, **kwargs):
        # Подключи сюда свой раннер задач / очередь / Celery и т.д.
        return {"status": "queued", "job_id": job_id, "kwargs": kwargs}

    async def worker_status():
        # Подключи сюда метрики своего рантайма (CPU, активные задачи, …)
        return {"jobs_running": 0, "status": "idle"}

    async def stop_worker():
        bridge.stop()
        return {"status": "stopping"}

    bridge.register("run_task", run_task)
    bridge.register("worker_status", worker_status)
    bridge.register("stop_worker", stop_worker)


def build_app() -> WorkerApp:
    return WorkerApp(
        server_url=os.getenv("NEXUSBRIDGEHUB_SERVER_URL"),
        project_id=os.getenv("NEXUSBRIDGEHUB_PROJECT_ID", "taskrelay"),
        user_id=os.getenv("NEXUSBRIDGEHUB_USER_ID", ""),
        token=os.getenv("NEXUSBRIDGEHUB_TOKEN", ""),
        pair_code=os.getenv("NEXUSBRIDGEHUB_PAIR_CODE", ""),
        register_fn=register_handlers,
    )


async def _main() -> None:
    app = build_app()
    await app.run()


if __name__ == "__main__":
    # С аргументами CLI — тонкий клиент (nexusbridgehub-worker)
    # Без аргументов — встраиваемый воркер с register_handlers
    if len(sys.argv) > 1:
        main_cli()
    else:
        asyncio.run(_main())
