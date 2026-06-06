#!/usr/bin/env python3
"""Controller that invokes the English-speaking worker."""

from __future__ import annotations

import asyncio
import os
import sys

from _bootstrap import DEFAULT_PROJECT_ID, DEFAULT_SERVER_URL, USER_EN

from nexusbridge.controller import BridgeController


async def main() -> None:
    token = os.getenv("CONTROLLER_TOKEN_EN", "")
    if not token:
        print("Set CONTROLLER_TOKEN_EN (see generate_tokens.py).", file=sys.stderr)
        sys.exit(1)

    ctrl = BridgeController(
        server_url=DEFAULT_SERVER_URL,
        token=token,
        project_id=DEFAULT_PROJECT_ID,
        user_id=USER_EN,
    )

    hello = await ctrl.invoke("say_hello", {"name": "World"})
    info = await ctrl.invoke("worker_info")

    print("say_hello ->", hello)
    print("worker_info ->", info)
    await ctrl.close()


if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info < (3, 14):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
