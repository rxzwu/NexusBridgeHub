"""Bridge worker client — embed in user projects."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from nexusbridgehub.protocol import (
    BridgeMessage,
    MessageType,
    Role,
    register_payload,
    result_payload,
)
from nexusbridgehub.utils import dumps_message, format_error, loads_message

_log = logging.getLogger("nexusbridgehub.client")

Handler = Callable[..., Any]
AsyncHandler = Callable[..., Awaitable[Any]]


class BridgeClient:
    """
    Worker-side client. Register local functions; server invokes them remotely.

    Typical usage:
        bridge = BridgeClient(server_url="wss://...", token=jwt, project_id="taskrelay", user_id="12345")
        bridge.register("run_task", run_task)
        bridge.register("worker_status", get_worker_status)
        await bridge.run()
    """

    def __init__(
        self,
        *,
        server_url: str,
        token: str,
        project_id: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
        reconnect_delay: float = 5.0,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.project_id = project_id
        self.user_id = str(user_id)
        self.metadata = metadata or {}
        self.reconnect_delay = reconnect_delay
        self._handlers: dict[str, Handler | AsyncHandler] = {}
        self._conn: ClientConnection | None = None
        self._stop = stop_event if stop_event is not None else asyncio.Event()

    def register(self, name: str, fn: Handler | AsyncHandler) -> None:
        self._handlers[name] = fn

    def register_function(self, name: str, fn: Handler | AsyncHandler) -> None:
        """Alias for plan compatibility."""
        self.register(name, fn)

    @property
    def functions(self) -> list[str]:
        return list(self._handlers.keys())

    async def _execute(self, name: str, args: dict[str, Any]) -> Any:
        fn = self._handlers.get(name)
        if not fn:
            raise KeyError(f"function '{name}' not registered")
        if inspect.iscoroutinefunction(fn):
            return await fn(**args)
        return fn(**args)

    async def _send(self, msg: BridgeMessage) -> None:
        if not self._conn:
            raise RuntimeError("not connected")
        await self._conn.send(dumps_message(msg.to_dict()))

    async def _register(self) -> None:
        msg = BridgeMessage(
            type=MessageType.REGISTER,
            payload=register_payload(
                role=Role.WORKER,
                project_id=self.project_id,
                user_id=self.user_id,
                functions=self.functions,
                metadata=self.metadata,
            ),
        )
        await self._send(msg)

    async def _handle_message(self, msg: BridgeMessage) -> None:
        if msg.type == MessageType.INVOKE:
            fn = str(msg.payload.get("function", ""))
            args = dict(msg.payload.get("args") or {})
            try:
                result = await self._execute(fn, args)
                reply = BridgeMessage(
                    type=MessageType.RESULT,
                    request_id=msg.request_id,
                    payload=result_payload(ok=True, result=result),
                )
            except Exception as exc:
                _log.exception("invoke %s failed", fn)
                reply = BridgeMessage(
                    type=MessageType.RESULT,
                    request_id=msg.request_id,
                    payload=result_payload(ok=False, error=format_error(exc)),
                )
            try:
                await self._send(reply)
            except Exception:
                _log.exception("failed to send result for %s", fn)
        elif msg.type == MessageType.REGISTER_ACK:
            _log.info("registered: %s", msg.payload)
        elif msg.type == MessageType.PING:
            await self._send(BridgeMessage(type=MessageType.PONG, request_id=msg.request_id))
        elif msg.type == MessageType.ERROR:
            _log.warning("server error: %s", msg.payload.get("error", msg.payload))
        else:
            _log.debug("ignored message type: %s", msg.type)

    async def _session(self) -> None:
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with websockets.connect(self.server_url, additional_headers=headers) as conn:
                self._conn = conn
                _log.info("connected project=%s user=%s", self.project_id, self.user_id)
                await self._register()
                async for raw in conn:
                    try:
                        msg = BridgeMessage.from_dict(loads_message(raw))
                        await self._handle_message(msg)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        _log.exception("failed to handle incoming message")
        finally:
            self._conn = None
            _log.info("session ended project=%s user=%s", self.project_id, self.user_id)

    async def run(self) -> None:
        """Connect loop with auto-reconnect. Survives handler and transport errors."""
        while not self._stop.is_set():
            try:
                await self._session()
            except asyncio.CancelledError:
                raise
            except websockets.ConnectionClosed as exc:
                _log.warning("disconnected: %s", exc)
            except OSError as exc:
                _log.warning("connection error: %s", exc)
            except Exception:
                _log.exception("unexpected session error")
            if self._stop.is_set():
                break
            _log.info("reconnecting in %.1fs...", self.reconnect_delay)
            await asyncio.sleep(self.reconnect_delay)

    def stop(self) -> None:
        self._stop.set()

    def run_sync(self) -> None:
        asyncio.run(self.run())
