#!/usr/bin/env python3
"""Minimal worker for English-speaking user (user-en)."""

from __future__ import annotations

import asyncio
import os
import sys

from _bootstrap import DEFAULT_PROJECT_ID, DEFAULT_SERVER_URL, USER_EN

from nexusbridge.client import BridgeClient


async def say_hello(name: str) -> str:
    return f"Hello, {name}!"


async def worker_info() -> dict:
    return {"locale": "en", "user_id": USER_EN, "status": "online"}


async def main() -> None:
    token = os.getenv("WORKER_TOKEN_EN", os.getenv("NEXUSBRIDGE_TOKEN", ""))
    if not token:
        print(
            "Set WORKER_TOKEN_EN (see generate_tokens.py).",
            file=sys.stderr,
        )
        sys.exit(1)

    bridge = BridgeClient(
        server_url=DEFAULT_SERVER_URL,
        token=token,
        project_id=DEFAULT_PROJECT_ID,
        user_id=USER_EN,
        metadata={"locale": "en", "demo": True},
    )
    bridge.register("say_hello", say_hello)
    bridge.register("worker_info", worker_info)

    print(f"[EN worker] connecting to {DEFAULT_SERVER_URL}, user_id={USER_EN}")
    await bridge.run()


if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info < (3, 14):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
