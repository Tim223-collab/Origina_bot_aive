#!/bin/bash

# 🚀 Скрипт автоматической установки AIVE на Ubuntu
# Использование: chmod +x install_ubuntu.sh && ./install_ubuntu.sh

set -e  # Останавливаться при ошибках

echo "🚀 Установка AIVE Bot на Ubuntu"
echo "================================"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка что запущено на Ubuntu/Debian
if [ ! -f /etc/debian_version ]; then
    print_error "Этот скрипт работает только на Ubuntu/Debian"
    exit 1
fi

# 1. Обновление системы
print_info "Обновление системы..."
sudo apt update
sudo apt upgrade -y

# 2. Установка зависимостей
print_info "Установка системных зависимостей..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    wget \
    curl \
    build-essential \
    libffi-dev \
    libssl-dev \
    libsqlite3-dev

# Проверка версии Python
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    print_error "Python версии 3.9+ требуется. Установлена: $PYTHON_VERSION"
    print_info "Устанавливаю Python 3.9..."
    sudo apt install -y software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python3.9 python3.9-venv python3.9-dev
    PYTHON_CMD="python3.9"
else
    PYTHON_CMD="python3"
    print_info "Python версия: $PYTHON_VERSION ✓"
fi

# 3. Создание виртуального окружения
print_info "Создание виртуального окружения..."
if [ -d "venv" ]; then
    print_warning "venv уже существует, пропускаю..."
else
    $PYTHON_CMD -m venv venv
fi

# 4. Активация venv и установка зависимостей
print_info "Установка Python зависимостей..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Установка Playwright
print_info "Установка Playwright и браузеров..."
playwright install chromium
sudo playwright install-deps chromium

# 6. Создание директорий
print_info "Создание необходимых директорий..."
mkdir -p data
mkdir -p data/screenshots
mkdir -p logs
mkdir -p memory-bank

chmod 755 data
chmod 755 data/screenshots
chmod 755 logs

# 7. Настройка .env
if [ ! -f ".env" ]; then
    print_info "Создание .env файла..."
    cat > .env << EOF
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ALLOWED_USER_IDS=123456789

# AI APIs
DEEPSEEK_API_KEY=your_deepseek_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# OpenWeather (опционально)
OPENWEATHER_API_KEY=your_weather_key

# Рабочий сайт (опционально)
WORK_SITE_URL=
WORK_SITE_USERNAME=
WORK_SITE_PASSWORD=

# База данных
DATABASE_PATH=data/bot.db
DATA_DIR=data

# Логирование
LOG_LEVEL=INFO
EOF
    chmod 600 .env
    print_warning ".env файл создан. ОБЯЗАТЕЛЬНО отредактируй его!"
    print_warning "nano .env"
else
    print_info ".env файл уже существует ✓"
fi

# 8. Создание systemd service
print_info "Создание systemd service..."
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

sudo tee /etc/systemd/system/aive-bot.service > /dev/null << EOF
[Unit]
Description=AIVE Telegram Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/python3 main.py
Restart=always
RestartSec=10

StandardOutput=append:$CURRENT_DIR/logs/bot.log
StandardError=append:$CURRENT_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

print_info "Systemd service создан ✓"

# 9. Создание вспомогательных скриптов
print_info "Создание вспомогательных скриптов..."

# update.sh
cat > update.sh << 'EOF'
#!/bin/bash
echo "🔄 Обновление AIVE Bot..."
cd "$(dirname "$0")"
sudo systemctl stop aive-bot
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl start aive-bot
sudo systemctl status aive-bot
echo "✅ Обновление завершено!"
EOF
chmod +x update.sh

# monitor.sh
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "🤖 AIVE Bot Monitor"
echo "==================="
STATUS=$(sudo systemctl is-active aive-bot)
echo "Status: $STATUS"
if [ "$STATUS" = "active" ]; then
    echo "✅ Bot is running"
    PID=$(pgrep -f "python3 main.py")
    echo "PID: $PID"
    UPTIME=$(ps -p $PID -o etime= 2>/dev/null | tr -d ' ')
    echo "Uptime: $UPTIME"
    MEM=$(ps -p $PID -o rss= 2>/dev/null | awk '{print $1/1024 " MB"}')
    echo "Memory: $MEM"
    CPU=$(ps -p $PID -o %cpu= 2>/dev/null)
    echo "CPU: $CPU%"
else
    echo "❌ Bot is NOT running"
fi
echo ""
echo "📊 Database size:"
du -h data/bot.db 2>/dev/null || echo "БД еще не создана"
echo ""
echo "📝 Recent logs (last 5 lines):"
tail -n 5 logs/bot.log 2>/dev/null || echo "Логов пока нет"
EOF
chmod +x monitor.sh

# backup.sh
mkdir -p ~/backups/aive-bot
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups/aive-bot
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE=$(pwd)/data/bot.db
if [ -f "$DB_FILE" ]; then
    cp $DB_FILE $BACKUP_DIR/bot_backup_$DATE.db
    gzip $BACKUP_DIR/bot_backup_$DATE.db
    echo "✅ Backup created: bot_backup_$DATE.db.gz"
    find $BACKUP_DIR -name "*.db.gz" -mtime +7 -delete
    echo "✅ Old backups cleaned"
else
    echo "❌ Database file not found"
fi
EOF
chmod +x backup.sh

print_info "Вспомогательные скрипты созданы ✓"

# 10. Активация systemd
print_info "Активация systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable aive-bot

echo ""
echo "================================"
echo "✅ Установка завершена!"
echo "================================"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1️⃣  Отредактируй .env файл:"
echo "   nano .env"
echo ""
echo "2️⃣  Запусти бота:"
echo "   sudo systemctl start aive-bot"
echo ""
echo "3️⃣  Проверь статус:"
echo "   sudo systemctl status aive-bot"
echo ""
echo "4️⃣  Просмотр логов:"
echo "   sudo journalctl -u aive-bot -f"
echo ""
echo "📚 Полезные команды:"
echo "   ./monitor.sh     - мониторинг бота"
echo "   ./update.sh      - обновление"
echo "   ./backup.sh      - бэкап БД"
echo ""
echo "📖 Документация: docs/UBUNTU_DEPLOY.md"
echo ""

# Деактивация venv
deactivate

