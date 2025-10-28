@echo off
chcp 65001 > nul 2>&1
echo ========================================
echo   Telegram AI Bot
echo ========================================
echo.

REM Проверка .env файла
if not exist .env (
    echo [X] Файл .env не найден!
    echo.
    echo Создайте .env файл:
    echo   1. copy .env.example .env
    echo   2. Отредактируйте .env
    echo   3. Запустите start.bat снова
    echo.
    pause
    exit /b 1
)

echo [OK] Файл .env найден
echo.

REM Проверка конфигурации
echo Проверка конфигурации...
python test_config.py
if errorlevel 1 (
    echo.
    echo [X] Ошибка конфигурации!
    echo Исправьте ошибки и запустите снова.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Запуск бота...
echo ========================================
echo.
echo Нажмите Ctrl+C для остановки
echo.

python main.py

pause

