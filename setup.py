"""
Скрипт для первичной настройки бота
"""
import asyncio
import sys
import os
from pathlib import Path

# Фикс кодировки для Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def setup():
    print("🚀 Настройка бота...\n")
    
    # Проверка .env файла
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Файл .env не найден!")
        print("📝 Создайте файл .env на основе .env.example")
        print("\nWindows: copy .env.example .env")
        print("Linux/Mac: cp .env.example .env")
        return False
    
    # Проверка зависимостей
    try:
        import telegram
        import playwright
        import aiohttp
        print("✅ Все зависимости установлены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e.name}")
        print("📦 Установите зависимости: pip install -r requirements.txt")
        return False
    
    # Проверка Playwright
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("✅ Playwright настроен")
    except Exception as e:
        print("⚠️ Playwright не настроен полностью")
        print("🔧 Выполните: playwright install chromium")
    
    # Проверка конфигурации
    try:
        import config
        config.validate_config()
        print("✅ Конфигурация валидна")
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("📝 Проверьте файл .env")
        return False
    
    # Инициализация БД
    try:
        from database import Database
        db = Database(config.DATABASE_PATH)
        await db.init_db()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False
    
    print("\n✨ Настройка завершена успешно!")
    print("🚀 Запустите бота: python main.py")
    return True

if __name__ == "__main__":
    result = asyncio.run(setup())
    sys.exit(0 if result else 1)

