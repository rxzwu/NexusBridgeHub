"""Integration tests for NexusBridge core loop."""

from __future__ import annotations

import asyncio
import socket

import pytest
import websockets

from nexusbridge.auth import AuthManager
from nexusbridge.client import BridgeClient
from nexusbridge.controller import BridgeController
from nexusbridge.crypto import decrypt_server_url, encrypt_server_url, generate_build_seed
from nexusbridge.protocol import BridgeMessage, MessageType, Role
from nexusbridge.server import BridgeServer
from nexusbridge.utils import dumps_message, loads_message

SECRET = "x" * 48 + "super-secret-bridge-key-2026"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def auth() -> AuthManager:
    return AuthManager(SECRET)


async def _run_server(auth: AuthManager, port: int) -> asyncio.Task:
    server = BridgeServer(auth, host="127.0.0.1", port=port)
    task = asyncio.create_task(server.run())
    await asyncio.sleep(0.3)
    return task


def test_encrypt_decrypt_roundtrip():
    seed = generate_build_seed()
    url = "wss://bridge.example.com:8765"
    enc = encrypt_server_url(url, seed)
    assert enc != url
    assert decrypt_server_url(enc, seed) == url


@pytest.mark.asyncio
async def test_worker_controller_invoke_loop(auth: AuthManager):
    port = _free_port()
    serve_task = await _run_server(auth, port)

    worker_token = auth.create_token(role=Role.WORKER, project_id="test", user_id="u1")
    ctrl_token = auth.create_token(role=Role.CONTROLLER, project_id="test", user_id="u1")

    bridge = BridgeClient(
        server_url=f"ws://127.0.0.1:{port}",
        token=worker_token,
        project_id="test",
        user_id="u1",
    )
    bridge.register("add", lambda a, b: a + b)
    worker_task = asyncio.create_task(bridge.run())
    await asyncio.sleep(0.5)

    ctrl = BridgeController(
        server_url=f"ws://127.0.0.1:{port}",
        token=ctrl_token,
        project_id="test",
        user_id="u1",
    )
    result = await ctrl.invoke("add", {"a": 2, "b": 3}, timeout=5)
    assert result == 5

    bridge.stop()
    worker_task.cancel()
    serve_task.cancel()
    await ctrl.close()
    with pytest.raises(asyncio.CancelledError):
        await serve_task


@pytest.mark.asyncio
async def test_pair_code_flow(auth: AuthManager):
    port = _free_port()
    serve_task = await _run_server(auth, port)

    code = auth.create_pair_code(project_id="taskrelay", user_id="999")
    async with websockets.connect(f"ws://127.0.0.1:{port}") as conn:
        msg = BridgeMessage(type=MessageType.PAIR_REQUEST, payload={"code": code})
        await conn.send(dumps_message(msg.to_dict()))
        raw = await conn.recv()
        reply = BridgeMessage.from_dict(loads_message(raw))
        assert reply.type == MessageType.PAIR_TOKEN
        assert reply.payload["project_id"] == "taskrelay"
        assert reply.payload["user_id"] == "999"
        assert reply.payload["token"]

    serve_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await serve_task
