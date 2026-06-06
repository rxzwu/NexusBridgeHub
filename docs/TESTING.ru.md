# Проверка NexusBridge (минимальный тест)

Пошаговая инструкция: сервер + два воркера (RU/EN) + контроллеры.  
Убедись, что мост работает **до** интеграции в боевой проект.

## Требования

- **Python 3.11 – 3.14** — полная поддержка (CI на каждом PR: 3.11, 3.12, 3.13, 3.14)
- **Python 3.10 и ниже** — не поддерживается

```powershell
python --version   # должно быть 3.11 или выше
```

## Что проверяем

| Шаг | Ожидание |
|-----|----------|
| Сервер стартует | Лог `starting on ws://0.0.0.0:8765` |
| RU worker online | Лог `worker online ... user=user-ru` |
| EN worker online | Лог `worker online ... user=user-en` |
| `controller_ru.py` | `say_hello -> Привет, Мир!` |
| `controller_en.py` | `say_hello -> Hello, World!` |

Два воркера с разными `user_id` показывают, что сервер **маршрутизирует** команды правильно: RU-контроллер не попадает на EN-воркер.

---

## Подготовка (один раз)

```powershell
cd C:\need\NexusBridgeSwag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Секрет (один на все терминалы этой сессии):

```powershell
$env:NEXUSBRIDGE_JWT_SECRET = "local-dev-secret-key-32chars-minimum!!"
```

---

## Терминал 1 — сервер

```powershell
cd C:\need\NexusBridgeSwag
.\.venv\Scripts\Activate.ps1
$env:NEXUSBRIDGE_JWT_SECRET = "local-dev-secret-key-32chars-minimum!!"
nexusbridge-server --host 127.0.0.1 --port 8765
```

Оставь окно открытым.

---

## Терминал 2 — генерация JWT

```powershell
cd C:\need\NexusBridgeSwag
.\.venv\Scripts\Activate.ps1
$env:NEXUSBRIDGE_JWT_SECRET = "local-dev-secret-key-32chars-minimum!!"
python examples\minimal\generate_tokens.py
```

Скопируй четыре строки токенов в переменные (подставь свои значения из вывода):

```powershell
$env:WORKER_TOKEN_RU = "..."
$env:WORKER_TOKEN_EN = "..."
$env:CONTROLLER_TOKEN_RU = "..."
$env:CONTROLLER_TOKEN_EN = "..."
```

---

## Терминал 3 — RU worker

```powershell
cd C:\need\NexusBridgeSwag
.\.venv\Scripts\Activate.ps1
$env:WORKER_TOKEN_RU = "..."   # из generate_tokens.py
python examples\minimal\worker_ru.py
```

Должно появиться: `[RU worker] подключение к ws://127.0.0.1:8765, user_id=user-ru`  
В логах сервера: `worker online project=demo_project user=user-ru`.

---

## Терминал 4 — EN worker (опционально, для проверки маршрутизации)

```powershell
cd C:\need\NexusBridgeSwag
.\.venv\Scripts\Activate.ps1
$env:WORKER_TOKEN_EN = "..."
python examples\minimal\worker_en.py
```

---

## Терминал 5 — RU controller

```powershell
cd C:\need\NexusBridgeSwag
.\.venv\Scripts\Activate.ps1
$env:CONTROLLER_TOKEN_RU = "..."
python examples\minimal\controller_ru.py
```

**Ожидаемый вывод:**

```
say_hello -> Привет, Мир!
worker_info -> {'locale': 'ru', 'user_id': 'user-ru', 'status': 'online'}
```

---

## Терминал 6 — EN controller

```powershell
cd C:\need\NexusBridgeSwag
.\.venv\Scripts\Activate.ps1
$env:CONTROLLER_TOKEN_EN = "..."
python examples\minimal\controller_en.py
```

**Ожидаемый вывод:**

```
say_hello -> Hello, World!
worker_info -> {'locale': 'en', 'user_id': 'user-en', 'status': 'online'}
```

---

## Типичные ошибки

| Сообщение | Причина | Решение |
|-----------|---------|---------|
| `no worker for demo_project/user-ru` | Воркер не запущен или упал | Запусти `worker_ru.py`, проверь токен |
| `missing JWT token` | Неверный или просроченный токен | Перегенерируй через `generate_tokens.py` |
| `connection refused` | Сервер не запущен | Терминал 1 |
| RU controller вернул English | Неверный `user_id` в токене | Токены RU/EN не перепутаны |

---

## bash (Linux / macOS)

```bash
export NEXUSBRIDGE_JWT_SECRET="local-dev-secret-key-32chars-minimum!!"

# T1
nexusbridge-server --host 127.0.0.1 --port 8765

# T2
python examples/minimal/generate_tokens.py
export WORKER_TOKEN_RU="..."
export CONTROLLER_TOKEN_RU="..."
export WORKER_TOKEN_EN="..."
export CONTROLLER_TOKEN_EN="..."

# T3–T6
python examples/minimal/worker_ru.py
python examples/minimal/worker_en.py
python examples/minimal/controller_ru.py
python examples/minimal/controller_en.py
```

---

## Следующий шаг

Когда минимальный тест проходит — переходи к [`examples/worker_integration.py`](../examples/worker_integration.py) и встраивай свои функции (`run_task`, `worker_status` и т.д.).
