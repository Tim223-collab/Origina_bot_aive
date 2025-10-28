@echo off
chcp 65001 > nul 2>&1
title Telegram AI Bot

REM Очистка кэша Python
echo Очистка кэша...
if exist __pycache__ rmdir /s /q __pycache__ 2>nul
if exist database\__pycache__ rmdir /s /q database\__pycache__ 2>nul
if exist services\__pycache__ rmdir /s /q services\__pycache__ 2>nul
if exist handlers\__pycache__ rmdir /s /q handlers\__pycache__ 2>nul
for /d %%d in (*) do if exist "%%d\__pycache__" rmdir /s /q "%%d\__pycache__" 2>nul
cls

echo ========================================
echo   Telegram AI Bot
echo ========================================
echo.

python -X utf8 main.py

echo.
echo Bot stopped.
pause

