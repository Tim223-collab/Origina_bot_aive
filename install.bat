@echo off
chcp 65001 > nul 2>&1
echo ================================
echo Installing Telegram AI Bot
echo ================================
echo.

echo [1/3] Установка Python пакетов...
pip install -r requirements.txt
if errorlevel 1 (
    echo Ошибка установки пакетов!
    pause
    exit /b 1
)

echo.
echo [2/3] Установка браузеров Playwright...
playwright install chromium
if errorlevel 1 (
    echo Ошибка установки Playwright!
    pause
    exit /b 1
)

echo.
echo [3/3] Настройка конфигурации...
if not exist .env (
    echo # Telegram Bot Configuration > .env
    echo TELEGRAM_BOT_TOKEN=your_bot_token_here >> .env
    echo ALLOWED_USER_IDS=your_telegram_id_here >> .env
    echo. >> .env
    echo # DeepSeek API >> .env
    echo DEEPSEEK_API_KEY=your_deepseek_api_key_here >> .env
    echo DEEPSEEK_MODEL=deepseek-chat >> .env
    echo. >> .env
    echo # Work Website Configuration >> .env
    echo WORK_SITE_URL=your_admin_panel_url_here >> .env
    echo WORK_SITE_USERNAME=your_username >> .env
    echo WORK_SITE_PASSWORD=your_password >> .env
    echo. >> .env
    echo # Bot Settings >> .env
    echo TIMEZONE=Europe/Moscow >> .env
    echo MAX_CONTEXT_MESSAGES=20 >> .env
    echo.
    echo Файл .env создан! Отредактируйте его своими данными.
) else (
    echo Файл .env уже существует.
)

echo.
echo ================================
echo Установка завершена!
echo ================================
echo.
echo Следующие шаги:
echo 1. Отредактируйте .env файл своими данными
echo 2. Запустите: python test_config.py (проверка)
echo 3. Запустите: start.bat (запуск бота)
echo.
pause

