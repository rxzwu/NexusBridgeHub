# Минимальное демо (воркеры RU + EN)

Два воркера с разными `user_id` — проверка маршрутизации на сервере.

| Файл | Назначение |
|------|------------|
| `generate_tokens.py` | Вывод JWT для воркеров и контроллеров |
| `worker_ru.py` | Воркер `user-ru`, ответы на русском |
| `worker_en.py` | Воркер `user-en`, ответы на английском |
| `controller_ru.py` | Вызов RU-воркера → `Привет, Мир!` |
| `controller_en.py` | Вызов EN-воркера → `Hello, World!` |

## Быстрый запуск

```powershell
$env:NEXUSBRIDGE_JWT_SECRET = "local-dev-secret-key-32chars-minimum!!"

# Терминал 1
nexusbridge-server --host 127.0.0.1 --port 8765

# Терминал 2
python examples\minimal\generate_tokens.py
# задай WORKER_TOKEN_* и CONTROLLER_TOKEN_* из вывода

# Терминалы 3–6
python examples\minimal\worker_ru.py
python examples\minimal\worker_en.py
python examples\minimal\controller_ru.py
python examples\minimal\controller_en.py
```

Полная инструкция: [docs/TESTING.ru.md](../../docs/TESTING.ru.md)
