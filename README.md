# NexusBridge

Universal bridge for distributed bot control: **bot → server → user worker**.

Add a thin integration layer to any Python bot or automation project — keep your business logic local, control it remotely through a central server.

## Architecture

```
┌─────────────┐   JWT controller   ┌──────────────┐   JWT worker   ┌─────────────────┐
│ Telegram    │ ────────────────► │ NexusBridge  │ ◄───────────── │ User Worker App │
│ Bot / API   │                   │   Server     │                │ (local runtime) │
└─────────────┘                   └──────────────┘                └─────────────────┘
```

| Component | Role |
|-----------|------|
| **Server** | Routes commands from bot to the correct user's worker |
| **BridgeClient** | Embedded in a project on the user's machine; executes registered functions |
| **BridgeController** | Used by a bot or API to invoke remote functions |
| **WorkerApp** | Thin standalone client; pairs via code, no secrets in binary |

## Security model

- **JWT tokens** — workers and controllers authenticate with short-lived tokens (no hardcoded secrets in the app)
- **Pair codes** — bot generates 8-char code; user enters it in the worker app → receives JWT
- **Encrypted server URL** — WSS address stored as AES-256-GCM blob with PBKDF2 key derivation + machine fingerprint (not plain text in `.exe`)
- **Thin client build** — `nexusbridge-build` generates per-build seed; combine with PyInstaller + optional commercial obfuscators

## Install

```bash
pip install nexusbridge
# or from source
pip install -e ".[dev]"
```

## Quick start

### 1. Start server (VPS)

```bash
export NEXUSBRIDGE_JWT_SECRET="your-48-char-minimum-secret-key-here"
nexusbridge-server --host 0.0.0.0 --port 8765
```

### 2. Embed in your project (user's machine)

```python
from nexusbridge import BridgeClient

bridge = BridgeClient(
    server_url="wss://bridge.example.com:8765",
    token=user_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
bridge.register("run_task", run_task)
bridge.register("worker_status", get_worker_status)
await bridge.run()
```

### 3. Bot side (controller on VPS)

```python
from nexusbridge import AuthManager, BridgeController
from nexusbridge.protocol import Role

auth = AuthManager(os.environ["NEXUSBRIDGE_JWT_SECRET"])

# Generate pair code for user (show in Telegram)
code = auth.create_pair_code(project_id="taskrelay", user_id=str(user_id))

# After user paired — invoke remote functions
bot_jwt = auth.create_token(role=Role.CONTROLLER, project_id="taskrelay", user_id=str(user_id))
ctrl = BridgeController(
    server_url="wss://bridge.example.com:8765",
    token=bot_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
result = await ctrl.invoke("run_task", {"job_id": "job-42"})
```

### 4. Thin client for users

```bash
# User runs with pair code from bot (no server URL visible)
nexusbridge-worker --pair-code ABCD1234

# Build distributable .exe with encrypted server URL
pip install nexusbridge[builder]
nexusbridge-build --server-url wss://bridge.example.com:8765 --output-dir worker_dist
```

## Per-user workers

Each end user runs a worker app on their own machine:

1. User opens the bot → bot shows a **pair code**
2. User runs the worker with that code → worker connects to your bridge server
3. Bot sends `run_task`, `worker_status`, etc. → commands execute on **the user's machine**
4. Local resources stay on the user's device — the bot only orchestrates

See [`examples/worker_integration.py`](examples/worker_integration.py) for a minimal integration example.

## Protocol

JSON messages over WebSocket:

| Type | Direction | Purpose |
|------|-----------|---------|
| `register` | client → server | Join as worker or controller |
| `invoke` | controller → worker | Call registered function |
| `result` | worker → controller | Return value or error |
| `pair_request` | worker → server | Redeem pair code for JWT |

## Development

```bash
pip install -e ".[dev]"
pytest
python -m build   # PyPI wheel
```

## License

MIT
