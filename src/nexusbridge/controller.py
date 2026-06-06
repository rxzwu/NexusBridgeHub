"""Controller client — used by Telegram bots / APIs to invoke remote workers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from nexusbridge.protocol import BridgeMessage, MessageType, Role, invoke_payload, register_payload
from nexusbridge.utils import dumps_message, loads_message

_log = logging.getLogger("nexusbridge.controller")


class BridgeController:
    """
    Bot-side client. Sends commands to a user's worker through the bridge server.

        ctrl = BridgeController(server_url="wss://...", token=bot_jwt, project_id="taskrelay", user_id="12345")
        result = await ctrl.invoke("run_task", {"job_id": "job-42"})
    """

    def __init__(
        self,
        *,
        server_url: str,
        token: str,
        project_id: str,
        user_id: str,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.project_id = project_id
        self.user_id = str(user_id)
        self._conn: ClientConnection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        headers = {"Authorization": f"Bearer {self.token}"}
        self._conn = await websockets.connect(self.server_url, additional_headers=headers)
        msg = BridgeMessage(
            type=MessageType.REGISTER,
            payload=register_payload(
                role=Role.CONTROLLER,
                project_id=self.project_id,
                user_id=self.user_id,
            ),
        )
        await self._conn.send(dumps_message(msg.to_dict()))
        raw = await asyncio.wait_for(self._conn.recv(), timeout=10)
        ack = BridgeMessage.from_dict(loads_message(raw))
        if ack.type != MessageType.REGISTER_ACK:
            raise RuntimeError(f"register failed: {ack.payload}")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def invoke(
        self,
        function: str,
        args: dict[str, Any] | None = None,
        *,
        timeout: float = 120,
    ) -> Any:
        async with self._lock:
            if not self._conn:
                await self.connect()

            assert self._conn is not None
            msg = BridgeMessage(
                type=MessageType.INVOKE,
                payload={
                    **invoke_payload(function=function, args=args),
                    "project_id": self.project_id,
                    "user_id": self.user_id,
                    "timeout": timeout,
                },
            )
            await self._conn.send(dumps_message(msg.to_dict()))
            raw = await asyncio.wait_for(self._conn.recv(), timeout=timeout + 5)
            reply = BridgeMessage.from_dict(loads_message(raw))

            if reply.type == MessageType.ERROR:
                raise RuntimeError(reply.payload.get("error", "unknown error"))
            if reply.type != MessageType.RESULT:
                raise RuntimeError(f"unexpected reply: {reply.type}")

            payload = reply.payload
            if not payload.get("ok"):
                raise RuntimeError(payload.get("error", "worker error"))
            return payload.get("result")

    async def worker_online(self) -> bool:
        async with self._lock:
            if not self._conn:
                await self.connect()
            assert self._conn is not None
            msg = BridgeMessage(
                type=MessageType.REGISTER,
                payload=register_payload(
                    role=Role.CONTROLLER,
                    project_id=self.project_id,
                    user_id=self.user_id,
                ),
            )
            await self._conn.send(dumps_message(msg.to_dict()))
            raw = await self._conn.recv()
            ack = BridgeMessage.from_dict(loads_message(raw))
            return bool(ack.payload.get("worker_online"))
