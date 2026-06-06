"""WebSocket bridge server — routes commands from controllers to workers."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

import websockets
from websockets.asyncio.server import ServerConnection

from nexusbridge.auth import AuthManager
from nexusbridge.protocol import (
    BridgeMessage,
    MessageType,
    Role,
    invoke_payload,
    register_payload,
    result_payload,
)
from nexusbridge.utils import dumps_message, loads_message, setup_logging

_log = logging.getLogger("nexusbridge.server")


@dataclass(slots=True)
class WorkerSession:
    conn: ServerConnection
    project_id: str
    user_id: str
    functions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ControllerSession:
    conn: ServerConnection
    project_id: str
    user_id: str


class BridgeServer:
    """Central hub: bot (controller) ↔ server ↔ user worker."""

    def __init__(self, auth: AuthManager, *, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.auth = auth
        self.host = host
        self.port = port
        self._workers: dict[tuple[str, str], WorkerSession] = {}
        self._controllers: dict[tuple[str, str], ControllerSession] = {}
        self._pending: dict[str, asyncio.Future[BridgeMessage]] = {}
        self._lock = asyncio.Lock()

    @property
    def worker_count(self) -> int:
        return len(self._workers)

    async def _send(self, conn: ServerConnection, msg: BridgeMessage) -> None:
        await conn.send(dumps_message(msg.to_dict()))

    async def _handle_register(
        self,
        conn: ServerConnection,
        msg: BridgeMessage,
        claims_token: str,
    ) -> None:
        claims = self.auth.verify_token(claims_token)
        payload = msg.payload
        role = Role(payload.get("role", claims.role.value))
        project_id = str(payload.get("project_id") or claims.project_id)
        user_id = str(payload.get("user_id") or claims.user_id)
        key = (project_id, user_id)

        async with self._lock:
            if role == Role.WORKER:
                session = WorkerSession(
                    conn=conn,
                    project_id=project_id,
                    user_id=user_id,
                    functions=list(payload.get("functions") or []),
                    metadata=dict(payload.get("metadata") or {}),
                )
                old = self._workers.get(key)
                if old and old.conn is not conn:
                    await old.conn.close(4001, "replaced by new worker")
                self._workers[key] = session
                _log.info("worker online project=%s user=%s funcs=%s", project_id, user_id, session.functions)
            else:
                session = ControllerSession(conn=conn, project_id=project_id, user_id=user_id)
                self._controllers[key] = session
                _log.info("controller online project=%s user=%s", project_id, user_id)

        worker = self._workers.get(key)
        ack = BridgeMessage(
            type=MessageType.REGISTER_ACK,
            request_id=msg.request_id,
            payload={
                "ok": True,
                "role": role.value,
                "worker_online": worker is not None,
                "worker_functions": worker.functions if worker else [],
            },
        )
        await self._send(conn, ack)

    async def _handle_invoke(self, conn: ServerConnection, msg: BridgeMessage) -> None:
        project_id = str(msg.payload.get("project_id", ""))
        user_id = str(msg.payload.get("user_id", ""))
        function = str(msg.payload.get("function", ""))
        args = dict(msg.payload.get("args") or {})
        timeout = float(msg.payload.get("timeout", 120))

        key = (project_id, user_id)
        worker = self._workers.get(key)
        if not worker:
            err = BridgeMessage(
                type=MessageType.ERROR,
                request_id=msg.request_id,
                payload={"error": f"no worker for {project_id}/{user_id}"},
            )
            await self._send(conn, err)
            return

        if function not in worker.functions:
            err = BridgeMessage(
                type=MessageType.ERROR,
                request_id=msg.request_id,
                payload={"error": f"function '{function}' not registered on worker"},
            )
            await self._send(conn, err)
            return

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[BridgeMessage] = loop.create_future()
        self._pending[msg.request_id] = fut

        invoke = BridgeMessage(
            type=MessageType.INVOKE,
            request_id=msg.request_id,
            payload=invoke_payload(function=function, args=args),
        )
        await self._send(worker.conn, invoke)

        try:
            result_msg = await asyncio.wait_for(fut, timeout=timeout)
            await self._send(conn, result_msg)
        except asyncio.TimeoutError:
            self._pending.pop(msg.request_id, None)
            err = BridgeMessage(
                type=MessageType.ERROR,
                request_id=msg.request_id,
                payload={"error": "worker timeout"},
            )
            await self._send(conn, err)

    async def _handle_result(self, msg: BridgeMessage) -> None:
        fut = self._pending.pop(msg.request_id, None)
        if fut and not fut.done():
            fut.set_result(msg)

    async def _handle_pair_request(self, conn: ServerConnection, msg: BridgeMessage) -> None:
        code = str(msg.payload.get("code", "")).upper()
        redeemed = self.auth.redeem_pair_code(code)
        if not redeemed:
            await self._send(
                conn,
                BridgeMessage(
                    type=MessageType.ERROR,
                    request_id=msg.request_id,
                    payload={"error": "invalid or expired pair code"},
                ),
            )
            return
        project_id, user_id = redeemed
        token = self.auth.create_token(role=Role.WORKER, project_id=project_id, user_id=user_id)
        await self._send(
            conn,
            BridgeMessage(
                type=MessageType.PAIR_TOKEN,
                request_id=msg.request_id,
                payload={"token": token, "project_id": project_id, "user_id": user_id},
            ),
        )

    async def _cleanup_connection(self, conn: ServerConnection) -> None:
        async with self._lock:
            for key, w in list(self._workers.items()):
                if w.conn is conn:
                    del self._workers[key]
                    _log.info("worker offline project=%s user=%s", key[0], key[1])
            for key, c in list(self._controllers.items()):
                if c.conn is conn:
                    del self._controllers[key]
                    _log.info("controller offline project=%s user=%s", key[0], key[1])

    async def _handler(self, conn: ServerConnection) -> None:
        auth_header = conn.request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip() if auth_header else ""
        try:
            async for raw in conn:
                data = loads_message(raw)
                msg = BridgeMessage.from_dict(data)

                if msg.type == MessageType.PING:
                    await self._send(conn, BridgeMessage(type=MessageType.PONG, request_id=msg.request_id))
                    continue

                if msg.type == MessageType.PAIR_REQUEST:
                    await self._handle_pair_request(conn, msg)
                    continue

                if msg.type == MessageType.REGISTER:
                    if not token:
                        token = str(msg.payload.get("token", ""))
                    if not token:
                        await self._send(
                            conn,
                            BridgeMessage(
                                type=MessageType.ERROR,
                                request_id=msg.request_id,
                                payload={"error": "missing JWT token"},
                            ),
                        )
                        continue
                    await self._handle_register(conn, msg, token)
                    continue

                if msg.type == MessageType.INVOKE:
                    await self._handle_invoke(conn, msg)
                    continue

                if msg.type == MessageType.RESULT:
                    await self._handle_result(msg)
                    continue

        except websockets.ConnectionClosed:
            pass
        finally:
            await self._cleanup_connection(conn)

    async def create_pair_code(self, *, project_id: str, user_id: str) -> str:
        return self.auth.create_pair_code(project_id=project_id, user_id=user_id)

    async def run(self) -> None:
        _log.info("starting on ws://%s:%s", self.host, self.port)
        async with websockets.serve(self._handler, self.host, self.port):
            await asyncio.Future()


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="NexusBridge server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("NEXUSBRIDGE_PORT", "8765")))
    parser.add_argument("--secret", default=os.getenv("NEXUSBRIDGE_JWT_SECRET", ""))
    args = parser.parse_args()
    if not args.secret:
        raise SystemExit("Set NEXUSBRIDGE_JWT_SECRET or pass --secret")

    setup_logging()
    auth = AuthManager(args.secret)
    server = BridgeServer(auth, host=args.host, port=args.port)
    asyncio.run(server.run())
