# Деплой NexusBridge на VPS (продакшен)

Пошаговая инструкция: поднять **NexusBridge Server** на VPS (Hetzner, Contabo или любой Ubuntu/Debian) с HTTPS/WSS, автозапуском и firewall.

> Локальная проверка перед продом: [TESTING.ru.md](TESTING.ru.md)

## Что получится

```
Интернет ──► VPS (443/wss) ──► Caddy/Nginx ──► nexusbridge-server (127.0.0.1:8765)
                                              ▲
                    Telegram-бот (controller) ──┤
                    Worker на ПК пользователя ──┘
```

| Компонент | Где крутится |
|-----------|--------------|
| `nexusbridge-server` | VPS |
| Бот / `BridgeController` | VPS (рядом с ботом) или отдельный сервер |
| `BridgeClient` / worker | Машина пользователя |

---

## 1. VPS и домен

### Hetzner Cloud

1. [console.hetzner.cloud](https://console.hetzner.cloud) → **Add Server**
2. **Ubuntu 24.04**, тип **CPX11** (2 vCPU / 2 GB) — достаточно для старта
3. SSH-ключ → Create
4. В **Firewalls**: открыть **22**, **80**, **443**; порт **8765 наружу не открывать** (только через reverse proxy)

### Contabo

1. VPS S (4 vCPU / 8 GB) или меньше — тоже хватит
2. OS: **Ubuntu 24.04**
3. После выдачи — root по SSH, сразу создай отдельного пользователя (см. ниже)

### Домен

A-запись `bridge.example.com` → IP VPS.  
Без домена Let's Encrypt не выдаст сертификат — для прода нужен домен.

---

## 2. Базовая настройка сервера

Подключись по SSH (замени IP):

```bash
ssh root@YOUR_VPS_IP
```

Создай пользователя (не работай от root):

```bash
adduser nexusbridge
usermod -aG sudo nexusbridge
rsync --archive --chown=nexusbridge:nexusbridge ~/.ssh /home/nexusbridge
```

Дальше — под пользователем `nexusbridge`:

```bash
ssh nexusbridge@YOUR_VPS_IP
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv curl ufw
```

Firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 3. JWT-секрет

Минимум **32 символа**. Сгенерируй один раз и **нигде не коммить**:

```bash
openssl rand -hex 32
```

Сохрани значение — оно нужно и серверу, и боту (`AuthManager`).

---

## 4. Установка NexusBridge

```bash
sudo mkdir -p /opt/nexusbridge
sudo chown nexusbridge:nexusbridge /opt/nexusbridge
cd /opt/nexusbridge

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "nexusbridge>=0.1.0"
```

Проверка:

```bash
which nexusbridge-server
# /opt/nexusbridge/.venv/bin/nexusbridge-server
```

---

## 5. systemd — автозапуск

Секрет храни в отдельном файле (права только root):

```bash
sudo bash -c 'cat > /etc/nexusbridge.env << EOF
NEXUSBRIDGE_JWT_SECRET=ВСТАВЬ_СЮДА_СЕКРЕТ_64_HEX_СИМВОЛА
NEXUSBRIDGE_PORT=8765
EOF'
sudo chmod 600 /etc/nexusbridge.env
sudo chown root:root /etc/nexusbridge.env
```

Unit-файл:

```bash
sudo tee /etc/systemd/system/nexusbridge.service << 'EOF'
[Unit]
Description=NexusBridge WebSocket server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=nexusbridge
Group=nexusbridge
WorkingDirectory=/opt/nexusbridge
EnvironmentFile=/etc/nexusbridge.env
ExecStart=/opt/nexusbridge/.venv/bin/nexusbridge-server --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nexusbridge
sudo systemctl status nexusbridge
```

В логах должно быть:

```text
starting on ws://127.0.0.1:8765
```

Логи: `journalctl -u nexusbridge -f`

---

## 6. HTTPS / WSS (reverse proxy)

Сервер слушает **ws://** локально. Снаружи клиенты подключаются по **wss://bridge.example.com**.

### Вариант A — Caddy (проще)

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

```bash
sudo tee /etc/caddy/Caddyfile << 'EOF'
bridge.example.com {
    reverse_proxy 127.0.0.1:8765
}
EOF
```

Замени `bridge.example.com` на свой домен.

```bash
sudo systemctl reload caddy
```

### Вариант B — Nginx

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

```bash
sudo tee /etc/nginx/sites-available/nexusbridge << 'EOF'
server {
    listen 80;
    server_name bridge.example.com;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/nexusbridge /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d bridge.example.com
```

---

## 7. Подключение бота и воркеров

URL для всех клиентов:

```text
wss://bridge.example.com
```

(без `:8765` — TLS терминируется на Caddy/Nginx)

### Бот (контроллер) на VPS

Тот же секрет, что в `/etc/nexusbridge.env`:

```bash
export NEXUSBRIDGE_JWT_SECRET="тот_же_секрет"
```

```python
ctrl = BridgeController(
    server_url="wss://bridge.example.com",
    token=bot_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
```

### Worker у пользователя

```python
bridge = BridgeClient(
    server_url="wss://bridge.example.com",
    token=user_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
```

Или тонкий клиент:

```bash
nexusbridge-worker --server-url wss://bridge.example.com --pair-code ABCD1234
```

---

## 8. Проверка после деплоя

### 8.1 Сервис жив

```bash
sudo systemctl is-active nexusbridge
curl -I https://bridge.example.com   # от Caddy/Nginx — не 502
```

### 8.2 WebSocket с VPS

```bash
source /opt/nexusbridge/.venv/bin/activate
pip install websockets
python3 << 'PY'
import asyncio, websockets
async def main():
    async with websockets.connect("wss://bridge.example.com") as ws:
        print("connected OK")
asyncio.run(main())
PY
```

### 8.3 Полный цикл

С локальной машины прогони [TESTING.ru.md](TESTING.ru.md), но в скриптах замени `ws://127.0.0.1:8765` на `wss://bridge.example.com`.

---

## 9. Обновление

```bash
cd /opt/nexusbridge
source .venv/bin/activate
pip install --upgrade nexusbridge
sudo systemctl restart nexusbridge
```

---

## 10. Чеклист безопасности

| ✓ | Действие |
|---|----------|
| ☐ | `NEXUSBRIDGE_JWT_SECRET` ≥ 32 символов, только на сервере и в боте |
| ☐ | Порт 8765 **не** открыт в firewall наружу |
| ☐ | TLS (HTTPS/WSS) включён |
| ☐ | SSH только по ключу, root login отключён |
| ☐ | `journalctl` / мониторинг — смотреть на `worker online` и ошибки auth |

---

## Troubleshooting

| Симптом | Решение |
|---------|---------|
| `502 Bad Gateway` | `systemctl status nexusbridge` — сервер не слушает 8765 |
| Worker не коннектится | Проверь `wss://`, не `ws://`; firewall 443 открыт |
| `JWT secret must be at least 32 characters` | Удлини секрет в `/etc/nexusbridge.env` |
| Pair-код не работает | Бот и сервер должны использовать **один** `NEXUSBRIDGE_JWT_SECRET` |
| Certbot fails | DNS A-запись ещё не пропагировалась — подожди 5–30 мин |

---

## Минимальные требования VPS

| Параметр | Значение |
|----------|----------|
| OS | Ubuntu 22.04 / 24.04 LTS |
| Python | 3.11 – 3.14 |
| RAM | 512 MB+ (1 GB комфортнее) |
| CPU | 1 vCPU |
| Диск | 10 GB |
| Порты наружу | 22, 80, 443 |

Этого достаточно, чтобы сразу запустить мост в проде.
