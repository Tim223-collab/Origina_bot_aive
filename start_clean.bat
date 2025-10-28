@echo off
chcp 65001 > nul 2>&1
echo ========================================
echo   Telegram AI Bot - Чистый запуск
echo ========================================
echo.

REM Удаляем кэш Python
echo Очистка кэша...
if exist __pycache__ rmdir /s /q __pycache__
if exist database\__pycache__ rmdir /s /q database\__pycache__
if exist services\__pycache__ rmdir /s /q services\__pycache__
if exist handlers\__pycache__ rmdir /s /q handlers\__pycache__
echo [OK] Кэш очищен
echo.

REM Проверка .env
if not exist .env (
    echo [X] Файл .env не найден!
    echo.
    echo Создайте .env файл:
    echo   1. copy .env.example .env
    echo   2. Отредактируйте .env
    echo   3. Запустите start_clean.bat снова
    echo.
    pause
    exit /b 1
)

echo [OK] Файл .env найден
echo.

REM Проверка конфигурации
echo Проверка конфигурации...
python -X utf8 test_config.py
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

python -X utf8 main.py

pause

