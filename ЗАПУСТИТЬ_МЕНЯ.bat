@echo off
chcp 65001 > nul 2>&1
title Telegram AI Bot - Запуск

echo.
echo ╔════════════════════════════════════════╗
echo ║   TELEGRAM AI BOT - ЗАПУСК            ║
echo ╚════════════════════════════════════════╝
echo.

REM Очистка кэша Python
echo [1/2] Очистка кэша Python...
if exist __pycache__ rmdir /s /q __pycache__ 2>nul
if exist database\__pycache__ rmdir /s /q database\__pycache__ 2>nul
if exist services\__pycache__ rmdir /s /q services\__pycache__ 2>nul
if exist handlers\__pycache__ rmdir /s /q handlers\__pycache__ 2>nul
echo [OK] Кэш очищен
echo.

REM Запуск бота
echo [2/2] Запуск бота...
echo.
python -X utf8 main.py

echo.
echo.
echo ════════════════════════════════════════
echo   Бот остановлен
echo ════════════════════════════════════════
echo.
pause

