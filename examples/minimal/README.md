# Minimal demo (RU + EN workers)

Two workers with different `user_id` values prove that the server routes commands correctly.

| File | Role |
|------|------|
| `generate_tokens.py` | Print JWT for workers and controllers |
| `worker_ru.py` | Worker for `user-ru`, responds in Russian |
| `worker_en.py` | Worker for `user-en`, responds in English |
| `controller_ru.py` | Calls RU worker → `Привет, Мир!` |
| `controller_en.py` | Calls EN worker → `Hello, World!` |

## Quick run

```bash
export NEXUSBRIDGE_JWT_SECRET="local-dev-secret-key-32chars-minimum!!"

# Terminal 1
nexusbridge-server --host 127.0.0.1 --port 8765

# Terminal 2
python examples/minimal/generate_tokens.py
# set WORKER_TOKEN_* and CONTROLLER_TOKEN_* from output

# Terminals 3–6
python examples/minimal/worker_ru.py
python examples/minimal/worker_en.py
python examples/minimal/controller_ru.py
python examples/minimal/controller_en.py
```

Full guide (RU): [docs/TESTING.ru.md](../../docs/TESTING.ru.md)
