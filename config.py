"""
Конфигурация бота
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = [int(id.strip()) for id in os.getenv("ALLOWED_USER_IDS", "").split(",") if id.strip()]

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Рабочий сайт
WORK_SITE_URL = os.getenv("WORK_SITE_URL")
WORK_SITE_USERNAME = os.getenv("WORK_SITE_USERNAME")
WORK_SITE_PASSWORD = os.getenv("WORK_SITE_PASSWORD")

# Дополнительные AI API (опционально)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Google Gemini API (для изображений)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Настройки бота
TIMEZONE = os.getenv("TIMEZONE", "Europe/Kiev")  # Украина
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))
DATABASE_PATH = DATA_DIR / "bot.db"

# Системные промпты для ИИ
SYSTEM_PROMPT = """Ты личный ИИ-помощник пользователя в Telegram. Твои характеристики:

- Дружелюбный и неформальный тон общения
- Отвечаешь кратко и по делу, но можешь развернуть ответ если попросят
- Помогаешь с рабочими задачами, напоминаниями, информацией
- Запоминаешь важные факты о пользователе
- Используешь эмодзи когда это уместно
- Можешь пошутить и поддержать разговор
- Знаешь русский, украинский и английский языки
- Пользователь находится в Украине (временная зона: Europe/Kiev)

🔧 ВАЖНО: У тебя есть доступ к функциям для получения РЕАЛЬНЫХ данных:
- get_work_stats - получает реальную статистику работников с сайта (SFS, SCH, скам)
- Когда пользователь спрашивает про работников, статистику, отчёты - ОБЯЗАТЕЛЬНО используй эту функцию!
- НЕ придумывай данные о работниках - всегда используй функцию для получения реальных данных!

Всегда общайся на русском языке, если не попросят иначе.
"""

# Валидация конфига
def validate_config():
    """Проверяет наличие обязательных параметров"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN не установлен")
    
    if not ALLOWED_USER_IDS:
        errors.append("ALLOWED_USER_IDS не установлен")
    
    if not DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY не установлен")
    
    if errors:
        raise ValueError(f"Ошибки конфигурации:\n" + "\n".join(f"- {e}" for e in errors))

if __name__ == "__main__":
    validate_config()
    print("✅ Конфигурация валидна!")

