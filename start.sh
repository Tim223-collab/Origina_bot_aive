#!/bin/bash

echo "========================================"
echo "  🤖 Telegram AI Bot"
echo "========================================"
echo ""

# Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo ""
    echo "Создайте .env файл:"
    echo "  1. cp .env.example .env"
    echo "  2. Отредактируйте .env"
    echo "  3. Запустите start.sh снова"
    echo ""
    exit 1
fi

echo "✅ Файл .env найден"
echo ""

# Проверка конфигурации
echo "🔍 Проверка конфигурации..."
python3 test_config.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Ошибка конфигурации!"
    echo "Исправьте ошибки и запустите снова."
    echo ""
    exit 1
fi

echo ""
echo "========================================"
echo "  🚀 Запуск бота..."
echo "========================================"
echo ""
echo "Нажмите Ctrl+C для остановки"
echo ""

python3 main.py

