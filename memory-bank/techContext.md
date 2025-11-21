# 🔧 Technical Context

## Технологический стек

### Core
- **Python**: 3.10+
- **Async**: asyncio, aiohttp, aiosqlite
- **Framework**: python-telegram-bot 21.5

### AI Models

#### Gemini 2.0 Flash (Primary)
```python
# Установка
pip install google-generativeai

# Использование
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

response = model.generate_content("Hello!")
print(response.text)
```

**Характеристики**:
- Бесплатно: 1500 запросов/день
- Контекст: 1M токенов
- Скорость: Очень быстрая
- Мультимодальность: Да (текст, изображения, видео)

**Лимиты**:
- Free tier: 15 RPM, 1M TPM
- Paid tier: 1000 RPM, 4M TPM

#### DeepSeek (Reasoning)
```python
# Уже интегрирован
# services/ai_service.py

response = await ai_service.reasoning_chat(
    "Сложная задача",
    use_reasoning=True
)
```

**Характеристики**:
- Стоимость: $0.14/$0.28 per 1M токенов
- Контекст: 32K токенов
- Reasoning mode: Да
- Function calling: Да

#### Claude 3.5 Sonnet (Optional)
```python
# Установка
pip install anthropic

# Использование
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)
```

**Характеристики**:
- Стоимость: $3/$15 per 1M токенов
- Контекст: 200K токенов
- Качество: Лучшее
- Эмпатия: Отличная

### Database

#### SQLite (Primary)
```python
# database/db.py
import aiosqlite

async def query(sql, params):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(sql, params)
        return await cursor.fetchall()
```

**Таблицы**:
- `users` - пользователи
- `conversations` - история
- `long_term_memory` - память
- `notes` - заметки
- `work_stats` - статистика
- `reminders` - напоминания
- `content_library` - контент

#### ChromaDB (Vector Search)
```python
# Установка
pip install chromadb

# Использование
import chromadb

client = chromadb.Client()
collection = client.create_collection("memory")

# Добавление
collection.add(
    documents=["Пользователь любит пиццу"],
    ids=["mem_1"]
)

# Поиск
results = collection.query(
    query_texts=["что любит пользователь?"],
    n_results=5
)
```

**Зачем**:
- Семантический поиск памяти
- Похожие факты
- Контекстуальные связи

### Web Scraping

#### Playwright
```python
# services/work_parser_service.py

from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url)
    # ... парсинг
```

**Возможности**:
- Headless браузер
- JavaScript поддержка
- Скриншоты
- Автоматизация

### Embeddings

#### Sentence Transformers
```python
# Установка
pip install sentence-transformers

# Использование
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embeddings = model.encode(["Текст на русском"])
```

**Модели**:
- `paraphrase-multilingual-MiniLM-L12-v2` - быстрая, мультиязычная
- `all-mpnet-base-v2` - качественная, английский
- `distiluse-base-multilingual-cased-v2` - универсальная

### Utilities

#### psutil (System Monitoring)
```python
import psutil

cpu_percent = psutil.cpu_percent()
memory = psutil.virtual_memory()
disk = psutil.disk_usage('/')
```

#### python-dotenv (Config)
```python
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
```

## Архитектура приложения

### Структура проекта
```
Origina_bot_aive/
├── main.py                 # Entry point
├── config.py              # Configuration
├── keyboards.py           # Telegram keyboards
│
├── database/              # Data layer
│   ├── __init__.py
│   ├── db.py             # Async SQLite operations
│   └── models.py         # SQL schemas
│
├── services/             # Business logic
│   ├── __init__.py
│   ├── ai_service.py          # AI models integration
│   ├── memory_service.py      # Memory management
│   ├── agent_service.py       # Proactive agent
│   ├── personality_service.py # Living personality
│   ├── content_library_service.py # Content library
│   ├── vision_service.py      # Image analysis
│   ├── extras_service.py      # Additional features
│   ├── function_tools.py      # Function executor
│   └── work_parser_service.py # Web scraping
│
├── handlers/             # Telegram handlers
│   ├── __init__.py
│   ├── ai_handler.py         # AI dialogue
│   ├── agent_handler.py      # Agent commands
│   ├── work_handler.py       # Work statistics
│   ├── utils_handler.py      # Memory, notes
│   ├── extras_handler.py     # Fun features
│   ├── menu_handler.py       # Menu system
│   ├── image_handler.py      # Image processing
│   └── content_handler.py    # Content library
│
├── data/                 # Data storage
│   ├── bot.db           # SQLite database
│   └── images/          # Saved images
│
├── memory-bank/         # Project knowledge
│   ├── projectBrief.md
│   ├── productContext.md
│   ├── systemPatterns.md
│   ├── techContext.md
│   ├── activeContext.md
│   └── progress.md
│
└── docs/                # Documentation
    ├── README.md
    ├── QUICKSTART.md
    ├── AI_AGENT.md
    └── ...
```

### Data Flow

```
Telegram Update
    ↓
Handler (маршрутизация)
    ↓
Service (бизнес-логика)
    ↓
AI Service / Database
    ↓
Response
    ↓
Telegram API
```

### Background Jobs

```python
# main.py

# Напоминания (каждую минуту)
app.job_queue.run_repeating(
    check_reminders,
    interval=60,
    first=10
)

# AI Агент (каждый час)
app.job_queue.run_repeating(
    check_agent,
    interval=3600,
    first=300
)

# Личность (каждые 30 мин)
app.job_queue.run_repeating(
    check_personality,
    interval=1800,
    first=600
)
```

## Environment Variables

### Required
```env
# Telegram
TELEGRAM_BOT_TOKEN=your_token
ALLOWED_USER_IDS=123456789

# AI APIs
DEEPSEEK_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
```

### Optional
```env
# Claude (для эмоциональных разговоров)
ANTHROPIC_API_KEY=sk-ant-xxx

# Work site (для парсинга)
WORK_SITE_URL=https://example.com
WORK_SITE_USERNAME=user
WORK_SITE_PASSWORD=pass

# Settings
TIMEZONE=Europe/Kiev
MAX_CONTEXT_MESSAGES=20
```

## Dependencies

### Core (`requirements.txt`)
```txt
# Telegram
python-telegram-bot==21.5

# AI
google-generativeai>=0.3.0
anthropic>=0.18.0

# Database
aiosqlite==0.20.0
chromadb>=0.4.0

# Embeddings
sentence-transformers>=2.2.0

# Web scraping
playwright==1.48.0

# HTTP
aiohttp==3.10.5

# System
psutil==6.0.0
python-dotenv==1.0.1
```

### Installation
```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Development Setup

### 1. Clone & Install
```bash
git clone <repo>
cd Origina_bot_aive
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your keys
```

### 3. Initialize DB
```bash
python -c "import asyncio; from database import Database; import config; asyncio.run(Database(config.DATABASE_PATH).init_db())"
```

### 4. Run
```bash
python main.py
```

## Production Setup

### Systemd Service
```ini
# /etc/systemd/system/aive-bot.service
[Unit]
Description=AIVE Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Commands
```bash
# Start
sudo systemctl start aive-bot

# Enable on boot
sudo systemctl enable aive-bot

# Check status
sudo systemctl status aive-bot

# Logs
sudo journalctl -u aive-bot -f
```

## Performance Considerations

### API Costs (Monthly)

**Free tier (recommended)**:
- Gemini 2.0 Flash: $0 (до 1500 req/день)
- DeepSeek: ~$1 (reasoning tasks)
- **Total: ~$1/месяц**

**With Claude**:
- Gemini: $0
- DeepSeek: ~$1
- Claude: ~$3-5 (emotional support)
- **Total: ~$4-6/месяц**

### Database Size
- SQLite: ~10-50 MB после месяца
- ChromaDB: ~100-500 MB (embeddings)
- Images: зависит от использования

### Memory Usage
- Python: ~100-200 MB
- Playwright: ~200-300 MB (когда активен)
- ChromaDB: ~100-200 MB
- **Total: ~400-700 MB**

### CPU Usage
- Idle: <1%
- Active dialogue: 5-10%
- Parsing: 20-30%
- Embeddings: 10-20%

## Testing

### Manual Testing
```bash
# Config validation
python test_config.py

# AI service
python -c "import asyncio; from services import AIService; print(asyncio.run(AIService().chat([{'role': 'user', 'content': 'test'}])))"

# Database
python -c "import asyncio; from database import Database; import config; asyncio.run(Database(config.DATABASE_PATH).init_db())"
```

### Unit Tests (TODO)
```bash
pytest tests/
```

## Troubleshooting

### Common Issues

**1. Event loop error (Windows)**
```python
# main.py
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

**2. Playwright not found**
```bash
playwright install chromium
```

**3. Database locked**
- Закрыть все подключения
- Проверить concurrent access

**4. API rate limits**
- Добавить exponential backoff
- Использовать кэширование

## Security

### Best Practices
- ✅ Secrets in `.env`
- ✅ `.gitignore` для секретов
- ✅ Whitelist пользователей
- ✅ Локальное хранение
- ✅ HTTPS для webhooks (если используются)

### Backups
```bash
# Backup database
cp data/bot.db data/bot_backup_$(date +%Y%m%d).db

# Backup ChromaDB
tar -czf chromadb_backup.tar.gz chroma_data/
```

---

**Дата создания**: 21.11.2024
**Последнее обновление**: 21.11.2024
**Версия**: 2.0

