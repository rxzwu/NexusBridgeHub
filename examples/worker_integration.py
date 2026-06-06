"""
Example: worker integration for a generic bot project.

The controller (bot/API) stays on a server; heavy work runs locally via the worker.
User flow:
  1. Bot generates pair code: auth.create_pair_code(project_id="taskrelay", user_id=user_id)
  2. User runs worker with --pair-code ABCD1234
  3. Bot sends commands via BridgeController.invoke(...)
"""

from __future__ import annotations

import asyncio
import os
import sys

# Allow running from repo without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nexusbridge.client import BridgeClient
from nexusbridge.worker_app import WorkerApp, main_cli


def register_handlers(bridge: BridgeClient) -> None:
    """Register functions exposed to the remote controller."""

    async def run_task(job_id: str, **kwargs):
        # Wire this to your project's task runner
        return {"status": "queued", "job_id": job_id, "kwargs": kwargs}

    async def worker_status():
        # Wire this to your project's runtime metrics
        return {"jobs_running": 0, "status": "idle"}

    async def stop_worker():
        bridge.stop()
        return {"status": "stopping"}

    bridge.register("run_task", run_task)
    bridge.register("worker_status", worker_status)
    bridge.register("stop_worker", stop_worker)


def build_app() -> WorkerApp:
    return WorkerApp(
        server_url=os.getenv("NEXUSBRIDGE_SERVER_URL"),
        project_id=os.getenv("NEXUSBRIDGE_PROJECT_ID", "taskrelay"),
        user_id=os.getenv("NEXUSBRIDGE_USER_ID", ""),
        token=os.getenv("NEXUSBRIDGE_TOKEN", ""),
        pair_code=os.getenv("NEXUSBRIDGE_PAIR_CODE", ""),
        register_fn=register_handlers,
    )


async def _main() -> None:
    app = build_app()
    await app.run()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_cli()
    else:
        asyncio.run(_main())
