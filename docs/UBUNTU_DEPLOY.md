# 🚀 Развертывание AIVE на Ubuntu Сервере

Пошаговое руководство для запуска бота на Ubuntu.

---

## 📋 Требования

- **Ubuntu:** 20.04+ (или Debian-based)
- **Python:** 3.9+
- **RAM:** минимум 1GB (рекомендуется 2GB)
- **Disk:** минимум 2GB свободного места

---

## 1️⃣ Подготовка Сервера

### Обновление Системы

```bash
# Обновляем пакеты
sudo apt update && sudo apt upgrade -y

# Устанавливаем необходимые пакеты
sudo apt install -y python3 python3-pip python3-venv git wget curl
```

### Установка Python 3.9+ (если нужно)

```bash
# Проверяем версию Python
python3 --version

# Если версия < 3.9, устанавливаем новую
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3.9-dev
```

---

## 2️⃣ Клонирование Проекта

### Создание Директории

```bash
# Создаем директорию для проекта
cd ~
mkdir -p projects
cd projects

# Клонируем репозиторий (или загружаем файлы)
# Вариант 1: Если есть git repo
git clone <your-repo-url> aive-bot
cd aive-bot

# Вариант 2: Если загружаем архив
# Загружаем через scp или wget
# scp -r /path/to/Origina_bot_aive user@server:~/projects/
```

---

## 3️⃣ Установка Зависимостей

### Создание Виртуального Окружения

```bash
# Создаем venv
python3 -m venv venv

# Активируем
source venv/bin/activate

# Проверяем что активировано (должно быть (venv) в начале строки)
which python3
# Должно показать: ~/projects/aive-bot/venv/bin/python3
```

### Установка Python Пакетов

```bash
# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt

# Может потребоваться установка дополнительных системных пакетов
# Если ошибки при установке aiosqlite:
sudo apt install -y libsqlite3-dev

# Если ошибки при установке других пакетов:
sudo apt install -y build-essential libffi-dev libssl-dev
```

### Установка Playwright

```bash
# Устанавливаем браузеры для Playwright
playwright install chromium

# Устанавливаем зависимости для chromium
playwright install-deps chromium

# Или все системные зависимости сразу:
sudo playwright install-deps
```

---

## 4️⃣ Настройка Конфигурации

### Создание .env Файла

```bash
# Копируем пример (если есть)
cp .env.example .env

# Или создаем новый
nano .env
```

### Заполнение .env

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ALLOWED_USER_IDS=123456789,987654321

# AI APIs
DEEPSEEK_API_KEY=your_deepseek_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# OpenWeather (опционально)
OPENWEATHER_API_KEY=your_weather_key

# Рабочий сайт (опционально)
WORK_SITE_URL=https://example.com
WORK_SITE_USERNAME=username
WORK_SITE_PASSWORD=password

# База данных
DATABASE_PATH=data/bot.db
DATA_DIR=data

# Логирование
LOG_LEVEL=INFO
```

**Сохранение в nano:**
- `Ctrl + O` → Enter (сохранить)
- `Ctrl + X` (выйти)

### Создание Директорий

```bash
# Создаем необходимые директории
mkdir -p data
mkdir -p data/screenshots
mkdir -p logs

# Проверяем права
chmod 755 data
chmod 755 data/screenshots
chmod 755 logs
```

---

## 5️⃣ Тестовый Запуск

### Проверка Конфигурации

```bash
# Активируем venv если не активирован
source venv/bin/activate

# Тестовый запуск
python3 main.py
```

**Если все ОК, увидишь:**
```
🚀 Инициализация бота...
✅ База данных инициализирована
🤖 AIVE инициализирован с моделями: ChatGPT, Gemini, DeepSeek
💙 Эмоциональный интеллект: активирован
✅ DTEK Parser registered
🤖 Бот запущен! Нажми Ctrl+C для остановки.
```

**Остановка:**
- `Ctrl + C`

---

## 6️⃣ Запуск в Фоне (Systemd)

### Создание Systemd Service

```bash
# Создаем service файл
sudo nano /etc/systemd/system/aive-bot.service
```

**Содержимое файла:**
```ini
[Unit]
Description=AIVE Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/projects/aive-bot
Environment="PATH=/home/YOUR_USERNAME/projects/aive-bot/venv/bin"
ExecStart=/home/YOUR_USERNAME/projects/aive-bot/venv/bin/python3 main.py
Restart=always
RestartSec=10

# Логи
StandardOutput=append:/home/YOUR_USERNAME/projects/aive-bot/logs/bot.log
StandardError=append:/home/YOUR_USERNAME/projects/aive-bot/logs/error.log

[Install]
WantedBy=multi-user.target
```

**❗ ВАЖНО:** Замени `YOUR_USERNAME` на свое имя пользователя!

```bash
# Проверить имя пользователя:
whoami
```

**Сохранение:**
- `Ctrl + O` → Enter
- `Ctrl + X`

### Активация Service

```bash
# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable aive-bot

# Запускаем
sudo systemctl start aive-bot

# Проверяем статус
sudo systemctl status aive-bot
```

**Если статус "active (running)" - все работает! ✅**

### Управление Ботом

```bash
# Запустить
sudo systemctl start aive-bot

# Остановить
sudo systemctl stop aive-bot

# Перезапустить
sudo systemctl restart aive-bot

# Статус
sudo systemctl status aive-bot

# Логи (последние 50 строк)
sudo journalctl -u aive-bot -n 50

# Логи в реальном времени
sudo journalctl -u aive-bot -f

# Отключить автозапуск
sudo systemctl disable aive-bot
```

---

## 7️⃣ Просмотр Логов

### Логи Systemd

```bash
# Последние 100 строк
sudo journalctl -u aive-bot -n 100

# Следить в реальном времени
sudo journalctl -u aive-bot -f

# Логи с ошибками
sudo journalctl -u aive-bot -p err

# Логи за сегодня
sudo journalctl -u aive-bot --since today
```

### Файловые Логи

```bash
# Основной лог
tail -f ~/projects/aive-bot/logs/bot.log

# Ошибки
tail -f ~/projects/aive-bot/logs/error.log

# Последние 100 строк
tail -n 100 ~/projects/aive-bot/logs/bot.log
```

---

## 8️⃣ Автоматическое Обновление

### Скрипт Обновления

Создай скрипт для обновления:

```bash
nano ~/projects/aive-bot/update.sh
```

**Содержимое:**
```bash
#!/bin/bash

# Переходим в директорию проекта
cd ~/projects/aive-bot

# Останавливаем бота
sudo systemctl stop aive-bot

# Обновляем код (если git)
git pull

# Активируем venv
source venv/bin/activate

# Обновляем зависимости
pip install -r requirements.txt --upgrade

# Перезапускаем бота
sudo systemctl start aive-bot

# Проверяем статус
sudo systemctl status aive-bot

echo "✅ Обновление завершено!"
```

**Делаем исполняемым:**
```bash
chmod +x ~/projects/aive-bot/update.sh
```

**Использование:**
```bash
~/projects/aive-bot/update.sh
```

---

## 9️⃣ Мониторинг

### Проверка Работоспособности

```bash
# Статус процесса
sudo systemctl status aive-bot

# Потребление ресурсов
top -p $(pgrep -f "python3 main.py")

# Или через htop (если установлен)
sudo apt install htop
htop -p $(pgrep -f "python3 main.py")

# Использование диска
du -sh ~/projects/aive-bot/*

# Размер БД
du -h ~/projects/aive-bot/data/bot.db
```

### Скрипт Мониторинга

```bash
nano ~/projects/aive-bot/monitor.sh
```

**Содержимое:**
```bash
#!/bin/bash

echo "🤖 AIVE Bot Monitor"
echo "==================="

# Статус
STATUS=$(sudo systemctl is-active aive-bot)
echo "Status: $STATUS"

if [ "$STATUS" = "active" ]; then
    echo "✅ Bot is running"
    
    # PID
    PID=$(pgrep -f "python3 main.py")
    echo "PID: $PID"
    
    # Uptime
    UPTIME=$(ps -p $PID -o etime= 2>/dev/null | tr -d ' ')
    echo "Uptime: $UPTIME"
    
    # Memory
    MEM=$(ps -p $PID -o rss= 2>/dev/null | awk '{print $1/1024 " MB"}')
    echo "Memory: $MEM"
    
    # CPU
    CPU=$(ps -p $PID -o %cpu= 2>/dev/null)
    echo "CPU: $CPU%"
else
    echo "❌ Bot is NOT running"
fi

echo ""
echo "📊 Database size:"
du -h ~/projects/aive-bot/data/bot.db

echo ""
echo "📝 Recent logs (last 5 lines):"
tail -n 5 ~/projects/aive-bot/logs/bot.log
```

**Делаем исполняемым:**
```bash
chmod +x ~/projects/aive-bot/monitor.sh
```

**Использование:**
```bash
~/projects/aive-bot/monitor.sh
```

---

## 🔟 Резервное Копирование

### Бэкап Базы Данных

```bash
# Создаем директорию для бэкапов
mkdir -p ~/backups/aive-bot

# Скрипт бэкапа
nano ~/projects/aive-bot/backup.sh
```

**Содержимое:**
```bash
#!/bin/bash

BACKUP_DIR=~/backups/aive-bot
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE=~/projects/aive-bot/data/bot.db

# Создаем бэкап
cp $DB_FILE $BACKUP_DIR/bot_backup_$DATE.db

# Сжимаем
gzip $BACKUP_DIR/bot_backup_$DATE.db

echo "✅ Backup created: bot_backup_$DATE.db.gz"

# Удаляем старые бэкапы (старше 7 дней)
find $BACKUP_DIR -name "*.db.gz" -mtime +7 -delete

echo "✅ Old backups cleaned"
```

**Делаем исполняемым:**
```bash
chmod +x ~/projects/aive-bot/backup.sh
```

### Автоматический Бэкап (Cron)

```bash
# Редактируем crontab
crontab -e

# Добавляем строку (бэкап каждый день в 3:00)
0 3 * * * ~/projects/aive-bot/backup.sh
```

---

## ⚠️ Решение Проблем

### Бот Не Запускается

```bash
# Проверяем логи
sudo journalctl -u aive-bot -n 50

# Проверяем конфигурацию
cd ~/projects/aive-bot
source venv/bin/activate
python3 -c "import config; config.validate_config()"

# Проверяем .env
cat .env | grep -v "^#" | grep -v "^$"

# Проверяем права
ls -la data/
```

### Ошибки с Playwright

```bash
# Переустанавливаем playwright
source venv/bin/activate
pip uninstall playwright -y
pip install playwright
playwright install chromium
sudo playwright install-deps
```

### Нехватка Памяти

```bash
# Проверяем память
free -h

# Добавляем swap (если нужно)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Делаем постоянным
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Бот Падает

```bash
# Проверяем логи ошибок
tail -n 100 ~/projects/aive-bot/logs/error.log

# Перезапускаем
sudo systemctl restart aive-bot

# Если не помогает - запускаем вручную для отладки
cd ~/projects/aive-bot
source venv/bin/activate
python3 main.py
```

---

## 📊 Полезные Команды

### Быстрая Шпаргалка

```bash
# Статус
sudo systemctl status aive-bot

# Перезапуск
sudo systemctl restart aive-bot

# Логи
sudo journalctl -u aive-bot -f

# Мониторинг
~/projects/aive-bot/monitor.sh

# Обновление
~/projects/aive-bot/update.sh

# Бэкап
~/projects/aive-bot/backup.sh

# Использование диска
du -sh ~/projects/aive-bot/*

# Размер БД
du -h ~/projects/aive-bot/data/bot.db
```

---

## 🔒 Безопасность

### Защита .env

```bash
# Права только для владельца
chmod 600 ~/projects/aive-bot/.env

# Проверяем
ls -la ~/projects/aive-bot/.env
# Должно быть: -rw------- (600)
```

### Firewall (UFW)

```bash
# Устанавливаем UFW (если нет)
sudo apt install ufw

# Разрешаем SSH
sudo ufw allow ssh

# Включаем firewall
sudo ufw enable

# Статус
sudo ufw status
```

### Обновления Безопасности

```bash
# Автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## ✅ Проверка Установки

После завершения установки проверь:

```bash
# 1. Бот запущен
sudo systemctl status aive-bot
# Должно быть: active (running)

# 2. Процесс работает
ps aux | grep "python3 main.py"

# 3. Порт не занят (если используется webhook)
# netstat -tulpn | grep :8443

# 4. Логи без критических ошибок
tail -n 50 ~/projects/aive-bot/logs/bot.log

# 5. БД создана
ls -lh ~/projects/aive-bot/data/bot.db

# 6. Telegram бот отвечает
# Напиши боту в Telegram: /start
```

---

## 🎯 Итоговая Последовательность

```bash
# 1. Обновить систему
sudo apt update && sudo apt upgrade -y

# 2. Установить зависимости
sudo apt install -y python3 python3-pip python3-venv git

# 3. Клонировать проект
cd ~ && mkdir -p projects && cd projects
# (загрузи файлы проекта)

# 4. Создать venv
cd aive-bot
python3 -m venv venv
source venv/bin/activate

# 5. Установить пакеты
pip install -r requirements.txt
playwright install chromium
sudo playwright install-deps

# 6. Настроить .env
nano .env
# (заполни API ключи)

# 7. Создать директории
mkdir -p data logs

# 8. Создать service
sudo nano /etc/systemd/system/aive-bot.service
# (скопируй конфиг из инструкции)

# 9. Запустить
sudo systemctl daemon-reload
sudo systemctl enable aive-bot
sudo systemctl start aive-bot

# 10. Проверить
sudo systemctl status aive-bot
```

---

## 📚 Дополнительно

### SSH Доступ

Для загрузки файлов на сервер:

```bash
# С локальной машины
scp -r /path/to/Origina_bot_aive user@server:~/projects/

# Или через rsync
rsync -avz --progress /path/to/Origina_bot_aive/ user@server:~/projects/aive-bot/
```

### Использование Screen/Tmux

Альтернатива systemd (проще для тестирования):

```bash
# Установка screen
sudo apt install screen

# Создание сессии
screen -S aive

# Запуск бота
cd ~/projects/aive-bot
source venv/bin/activate
python3 main.py

# Отключиться: Ctrl+A, затем D

# Вернуться
screen -r aive

# Убить сессию
screen -X -S aive quit
```

---

## 🎉 Готово!

Теперь AIVE работает на твоем Ubuntu сервере! 🚀

**Полезные ссылки:**
- [Документация Systemd](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Python venv](https://docs.python.org/3/library/venv.html)
- [Playwright Docs](https://playwright.dev/python/docs/intro)

**Возникли проблемы?** Проверь логи:
```bash
sudo journalctl -u aive-bot -n 100
```

---

**Made with 💙 by AIVE Team**

