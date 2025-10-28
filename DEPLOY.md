# 🚀 Деплой на домашний сервер

## Вариант 1: Systemd Service (Linux)

### 1. Подготовка

```bash
# Перенеси проект на сервер
scp -r "Бот мне" user@server:/home/user/telegram-bot

# Подключись к серверу
ssh user@server

# Перейди в директорию
cd /home/user/telegram-bot
```

### 2. Установка зависимостей

```bash
# Установи Python 3.10+ если нет
sudo apt update
sudo apt install python3 python3-pip

# Установи зависимости
pip3 install -r requirements.txt
playwright install chromium
```

### 3. Настройка .env

```bash
# Отредактируй .env
nano .env

# Проверь конфигурацию
python3 test_config.py
```

### 4. Настройка systemd

```bash
# Отредактируй bot.service
nano bot.service

# Измени:
# - YOUR_USER на твоего пользователя
# - /path/to/bot/directory на реальный путь

# Скопируй service файл
sudo cp bot.service /etc/systemd/system/telegram-bot.service

# Создай директорию для логов
sudo mkdir -p /var/log/telegram-bot
sudo chown $USER:$USER /var/log/telegram-bot

# Перезагрузи systemd
sudo systemctl daemon-reload

# Включи автозапуск
sudo systemctl enable telegram-bot

# Запусти бота
sudo systemctl start telegram-bot
```

### 5. Управление ботом

```bash
# Статус
sudo systemctl status telegram-bot

# Логи
sudo journalctl -u telegram-bot -f

# Перезапуск
sudo systemctl restart telegram-bot

# Остановка
sudo systemctl stop telegram-bot
```

## Вариант 2: Screen (простой способ)

```bash
# Установи screen
sudo apt install screen

# Создай сессию
screen -S telegram-bot

# Запусти бота
python3 main.py

# Отключись от сессии: Ctrl+A затем D

# Вернись к сессии
screen -r telegram-bot

# Список сессий
screen -ls
```

## Вариант 3: Docker (опционально)

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

CMD ["python", "main.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    container_name: telegram-ai-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
```

### Запуск

```bash
docker-compose up -d
docker-compose logs -f
```

## Автообновление

### Создай скрипт update.sh

```bash
#!/bin/bash
cd /home/user/telegram-bot
git pull
pip3 install -r requirements.txt
sudo systemctl restart telegram-bot
```

### Cron задача для автообновления (опционально)

```bash
crontab -e

# Проверка обновлений каждый день в 3:00
0 3 * * * /home/user/telegram-bot/update.sh >> /var/log/telegram-bot/update.log 2>&1
```

## Резервное копирование

### Создай скрипт backup.sh

```bash
#!/bin/bash
BACKUP_DIR="/home/user/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап базы данных
cp /home/user/telegram-bot/data/bot.db $BACKUP_DIR/bot_$DATE.db

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "bot_*.db" -mtime +30 -delete
```

### Cron для бэкапов

```bash
crontab -e

# Бэкап каждый день в 2:00
0 2 * * * /home/user/telegram-bot/backup.sh
```

## Мониторинг

### Проверка работоспособности

```bash
# Простая проверка процесса
ps aux | grep main.py

# Проверка портов (если используется)
netstat -tuln | grep LISTEN

# Использование ресурсов
top -p $(pgrep -f main.py)
```

### Алерты при падении (опционально)

Добавь в cron:

```bash
*/5 * * * * systemctl is-active --quiet telegram-bot || systemctl restart telegram-bot
```

## Безопасность

1. **Права доступа:**
```bash
chmod 600 .env
chmod 644 data/bot.db
```

2. **Firewall:**
```bash
# Закрой ненужные порты
sudo ufw enable
sudo ufw allow ssh
```

3. **Регулярные обновления:**
```bash
sudo apt update && sudo apt upgrade -y
```

## Проблемы и решения

### Бот не запускается
```bash
# Проверь логи
sudo journalctl -u telegram-bot -n 50

# Проверь конфигурацию
python3 test_config.py
```

### Нет прав на файлы
```bash
sudo chown -R $USER:$USER /home/user/telegram-bot
chmod -R 755 /home/user/telegram-bot
```

### Playwright не работает в headless
```bash
# Установи зависимости системы
playwright install-deps chromium
```

---

**Готово! Бот работает 24/7 на твоем сервере! 🎉**

