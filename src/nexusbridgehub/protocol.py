"""Wire protocol for NexusBridgeHub: bot → server → worker."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    WORKER = "worker"
    CONTROLLER = "controller"


class MessageType(StrEnum):
    REGISTER = "register"
    REGISTER_ACK = "register_ack"
    INVOKE = "invoke"
    RESULT = "result"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    PAIR_REQUEST = "pair_request"
    PAIR_TOKEN = "pair_token"
    WORKER_STATUS = "worker_status"


@dataclass(slots=True)
class BridgeMessage:
    type: MessageType
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type.value, "payload": self.payload}
        if self.request_id:
            data["request_id"] = self.request_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BridgeMessage":
        return cls(
            type=MessageType(data["type"]),
            payload=data.get("payload") or {},
            request_id=data.get("request_id") or str(uuid.uuid4()),
        )


def register_payload(
    *,
    role: Role,
    project_id: str,
    user_id: str,
    functions: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "role": role.value,
        "project_id": project_id,
        "user_id": user_id,
        "functions": functions or [],
        "metadata": metadata or {},
    }


def invoke_payload(*, function: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"function": function, "args": args or {}}


def result_payload(*, ok: bool, result: Any = None, error: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {"ok": ok}
    if ok:
        data["result"] = result
    else:
        data["error"] = error or "unknown error"
    return data
