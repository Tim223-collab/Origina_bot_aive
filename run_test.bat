@echo off
chcp 65001 > nul 2>&1
echo Запуск проверки конфигурации...
echo.
python -X utf8 test_config.py
echo.
pause

