"""
Быстрая проверка конфигурации
"""
import sys
import os
from pathlib import Path

# Фикс кодировки для Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

def check_config():
    """Проверяет все настройки"""
    
    print("🔍 Проверка конфигурации...\n")
    
    errors = []
    warnings = []
    
    # Проверка .env
    if not Path(".env").exists():
        errors.append(".env файл не найден")
        print("❌ .env файл не найден")
        print("   Создайте: copy .env.example .env\n")
    else:
        print("✅ .env файл найден\n")
    
    # Импорт конфига
    try:
        import config
        print("✅ Конфигурация загружена\n")
    except Exception as e:
        errors.append(f"Ошибка загрузки конфига: {e}")
        print(f"❌ Ошибка загрузки конфига: {e}\n")
        return False
    
    # Проверка Telegram
    print("📱 Telegram:")
    if not config.TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN не установлен")
        print("   ❌ Bot Token не установлен")
    else:
        token_preview = config.TELEGRAM_BOT_TOKEN[:10] + "..."
        print(f"   ✅ Bot Token: {token_preview}")
    
    if not config.ALLOWED_USER_IDS:
        errors.append("ALLOWED_USER_IDS не установлен")
        print("   ❌ User IDs не установлены")
    else:
        print(f"   ✅ Разрешенные пользователи: {config.ALLOWED_USER_IDS}")
    print()
    
    # Проверка DeepSeek
    print("🤖 DeepSeek AI:")
    if not config.DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY не установлен")
        print("   ❌ API Key не установлен")
    else:
        key_preview = config.DEEPSEEK_API_KEY[:10] + "..."
        print(f"   ✅ API Key: {key_preview}")
        print(f"   ✅ Модель: {config.DEEPSEEK_MODEL}")
    print()
    
    # Проверка рабочего сайта
    print("🌐 Рабочий сайт:")
    if not config.WORK_SITE_URL:
        warnings.append("WORK_SITE_URL не установлен (опционально)")
        print("   ⚠️ URL не установлен (опционально)")
    else:
        print(f"   ✅ URL: {config.WORK_SITE_URL}")
        print(f"   ✅ Username: {config.WORK_SITE_USERNAME}")
    print()
    
    # Проверка зависимостей
    print("📦 Зависимости:")
    deps = {
        "telegram": "python-telegram-bot",
        "playwright": "playwright",
        "aiohttp": "aiohttp",
        "dotenv": "python-dotenv",
        "aiosqlite": "aiosqlite",
    }
    
    missing_deps = []
    for module, package in deps.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            missing_deps.append(package)
            print(f"   ❌ {package}")
    
    if missing_deps:
        errors.append(f"Отсутствуют зависимости: {', '.join(missing_deps)}")
        print(f"\n   Установите: pip install {' '.join(missing_deps)}")
    print()
    
    # Проверка Playwright
    print("🎭 Playwright:")
    try:
        from playwright.sync_api import sync_playwright
        print("   ✅ Установлен")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            print("   ✅ Браузеры установлены")
        except Exception as e:
            warnings.append("Playwright браузеры не установлены")
            print("   ⚠️ Браузеры не установлены")
            print("   Выполните: playwright install chromium")
    except ImportError:
        errors.append("Playwright не установлен")
        print("   ❌ Не установлен")
    print()
    
    # Проверка БД
    print("💾 База данных:")
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir()
        print("   ✅ Директория создана")
    else:
        print("   ✅ Директория существует")
    print()
    
    # Итоги
    print("=" * 50)
    if errors:
        print("\n❌ Найдены критические ошибки:\n")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
        print("\nИсправьте ошибки перед запуском!")
        return False
    elif warnings:
        print("\n⚠️ Предупреждения:\n")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
        print("\n✅ Можно запускать, но некоторые функции могут не работать.")
        return True
    else:
        print("\n✅ Все проверки пройдены успешно!")
        print("\n🚀 Можно запускать бота: python main.py")
        return True

if __name__ == "__main__":
    try:
        success = check_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Ошибка проверки: {e}")
        sys.exit(1)

