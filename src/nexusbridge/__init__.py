"""
NexusBridge — universal distributed control bridge.

Architecture: bot (controller) → server → user worker (thin client)

    ┌─────────────┐     WebSocket      ┌──────────────┐     WebSocket     ┌─────────────┐
    │ Telegram    │ ─────────────────► │ NexusBridge  │ ◄──────────────── │ User Worker │
    │ Bot / API   │   JWT controller   │   Server     │   JWT worker      │ (local app) │
    └─────────────┘                    └──────────────┘                   └─────────────┘

Quick start (worker in your project):

    from nexusbridge import BridgeClient

    bridge = BridgeClient(
        server_url="wss://bridge.example.com:8765",
        token=jwt_token,
        project_id="taskrelay",
        user_id="123456789",
    )
    bridge.register("run_task", my_run_task)
    await bridge.run()

Quick start (bot side):

    from nexusbridge import BridgeController

    ctrl = BridgeController(server_url="...", token=bot_jwt, project_id="taskrelay", user_id="123456789")
    result = await ctrl.invoke("run_task", {"job_id": "job-42"})
"""

from nexusbridge.auth import AuthManager, TokenClaims
from nexusbridge.client import BridgeClient
from nexusbridge.controller import BridgeController
from nexusbridge.crypto import (
    decrypt_server_url,
    encrypt_server_url,
    generate_build_seed,
    obfuscate_seed,
    deobfuscate_seed,
)
from nexusbridge.protocol import BridgeMessage, MessageType, Role
from nexusbridge.server import BridgeServer

__all__ = [
    "AuthManager",
    "BridgeClient",
    "BridgeController",
    "BridgeMessage",
    "BridgeServer",
    "MessageType",
    "Role",
    "TokenClaims",
    "decrypt_server_url",
    "deobfuscate_seed",
    "encrypt_server_url",
    "generate_build_seed",
    "obfuscate_seed",
]

__version__ = "0.1.0"
