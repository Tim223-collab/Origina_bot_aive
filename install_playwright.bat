@echo off
chcp 65001 > nul 2>&1
echo ========================================
echo   Установка Playwright
echo ========================================
echo.

echo [1/2] Установка Playwright...
pip install playwright
if errorlevel 1 (
    echo Ошибка установки!
    pause
    exit /b 1
)

echo.
echo [2/2] Установка браузера Chromium...
playwright install chromium
if errorlevel 1 (
    echo Ошибка установки браузера!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Установка завершена!
echo ========================================
echo.
echo Теперь можно запускать бота:
echo   start.bat
echo.
pause

