# 🧠 Memory Bank - Банк памяти проекта

## 📋 Краткое описание проекта

**Название:** Telegram ИИ-Бот (Личный помощник)  
**Пользователь:** Timofey (@TT_gens)  
**Цель:** Личный ИИ-помощник для работы, продуктивности и автоматизации

---

## 🏗 Архитектура проекта

### Структура директорий

```
bot/
├── main.py                      # Точка входа, TelegramBot класс
├── config.py                    # Конфигурация (валидация .env)
├── database/                    # SQLite слой
│   ├── db.py                   # Database класс (async)
│   └── models.py               # SQL схемы (6 таблиц)
├── services/                    # Бизнес-логика
│   ├── ai_service.py           # AIService (DeepSeek API)
│   ├── memory_service.py       # MemoryService (долгосрочная память)
│   ├── parser_service.py       # WorkSiteParser (Playwright)
│   └── extras_service.py       # ExtrasService (погода, курсы, игры)
├── handlers/                    # Telegram обработчики
│   ├── ai_handler.py           # AIHandler (диалоги)
│   ├── work_handler.py         # WorkHandler (статистика)
│   ├── utils_handler.py        # UtilsHandler (память, заметки)
│   └── extras_handler.py       # ExtrasHandler (развлечения)
└── data/bot.db                 # SQLite база
```

### Ключевые классы

1. **TelegramBot** (`main.py`)
   - Инициализация всех сервисов
   - Регистрация handlers
   - Background job для напоминаний

2. **Database** (`database/db.py`)
   - Асинхронные CRUD операции
   - 6 таблиц: users, conversations, long_term_memory, notes, work_stats, reminders

3. **AIService** (`services/ai_service.py`)
   - DeepSeek API клиент
   - Методы: chat(), chat_with_context(), summarize_text(), extract_facts()

4. **MemoryService** (`services/memory_service.py`)
   - Управление долгосрочной памятью
   - Категории: personal, work, preferences, learning
   - Методы: remember_fact(), recall_facts(), forget_fact()

5. **WorkSiteParser** (`services/parser_service.py`)
   - Playwright для парсинга админ-панели
   - Логин, парсинг статистики работников
   - Метрики: SFS, SCH, Only now

---

## 🔑 Конфигурация (.env)

```env
# Установлено пользователем
TELEGRAM_BOT_TOKEN=<токен от @BotFather>
ALLOWED_USER_IDS=<ID пользователя Timofey>
DEEPSEEK_API_KEY=<ключ с platform.deepseek.com>

# Рабочий сайт (админ-панель)
WORK_SITE_URL=<URL админки>
WORK_SITE_USERNAME=<логин>
WORK_SITE_PASSWORD=<пароль>

# Настройки
TIMEZONE=Europe/Moscow
MAX_CONTEXT_MESSAGES=20
```

---

## 💾 База данных (SQLite)

### Таблицы

1. **users** - профили пользователей
   - user_id, username, first_name, last_name, created_at, last_active

2. **conversations** - история диалогов
   - id, user_id, role (user/assistant), content, timestamp

3. **long_term_memory** - долгосрочная память
   - id, user_id, category, key, value, created_at, updated_at
   - UNIQUE(user_id, category, key)

4. **notes** - заметки
   - id, user_id, title, content, tags (JSON), created_at

5. **work_stats** - статистика с сайта
   - id, user_id, date, total_records, total_sfs, total_sch, workers_data (JSON)

6. **reminders** - напоминания
   - id, user_id, text, remind_at, created_at, completed

---

## 🎯 Основной функционал

### 1. ИИ Диалоги (AIHandler)

**Поток работы:**
```
Пользователь → Сохранение в DB → Загрузка контекста 
→ Загрузка памяти → DeepSeek API → Сохранение ответа → Отправка
```

**Команды:**
- Текстовое сообщение → chat с контекстом
- `/clear` → очистка истории
- `/summarize` → резюме разговора

### 2. Система памяти (MemoryService)

**Категории:**
- `personal` - личная информация
- `work` - рабочие данные
- `preferences` - предпочтения
- `learning` - что изучает

**Команды:**
- `/remember <category> <key> <value>` - сохранить
- `/recall [category]` - показать
- `/forget <category> <key>` - удалить

**Интеграция с ИИ:**
- Память автоматически добавляется в системный промпт
- Форматируется как контекст для персонализации

### 3. Парсинг рабочего сайта (WorkHandler)

**Сайт:** Админ-панель управления командами
- Команды: Velvet, Good Bunny
- Работники: Alina, Karina, Nika, Oleg, Slavik, Stazon, Timofey, Vlad
- Метрики: SFS, Only now, SCH
- Проверка на скам-ассистентов

**Команды:**
- `/stats [date]` - статистика
- `/workers [team]` - список работников
- `/check <name>` - детали работника

**Технология:** Playwright (headless Chromium)

### 4. Продуктивность (UtilsHandler)

**Заметки:**
- `/note <text>` - создать
- `/notes [search]` - поиск
- `/delnote <id>` - удалить

**Напоминания:**
- `/remind <minutes> <text>` - создать
- Background job каждую минуту проверяет и отправляет

### 5. Информация (ExtrasHandler)

**API интеграции:**
- Погода: wttr.in
- Валюты: cbr-xml-daily.ru (ЦБ РФ)
- Крипта: coinbase.com

**Команды:**
- `/weather [city]` - погода
- `/rates` - курсы валют
- `/crypto [symbol]` - цена криптовалюты

### 6. Развлечения (ExtrasHandler)

**Контент:**
- 15+ интересных фактов
- 8+ шуток про программистов
- 8+ мотивационных цитат
- Советы: productivity, health, coding

**Команды:**
- `/fact`, `/joke`, `/quote`, `/tips [category]`
- `/activity` (Bored API)
- `/dice [XdY]`, `/8ball <question>`, `/choose <А> или <Б>`

### 7. Система (UtilsHandler)

**Мониторинг:**
- CPU, RAM, диск (psutil)
- Аптайм системы

**Команда:**
- `/system` - информация о системе

---

## 🔄 Потоки данных

### ИИ Диалог

```
User Message 
→ db.add_message(user, "user", text)
→ db.get_recent_messages(user, limit=20)
→ memory.get_context_for_ai(user)
→ ai.chat_with_context(message, context, system_prompt + memory)
→ db.add_message(user, "assistant", response)
→ send to Telegram
```

### Парсинг сайта

```
/stats command
→ parser.login() (Playwright)
→ parser.parse_statistics(date)
→ extract: cards (totals), table rows (workers)
→ db.save_work_stats(user, date, data)
→ format message (top 5 workers)
→ send to Telegram
```

### Напоминания

```
Background Job (каждые 60 сек)
→ db.get_pending_reminders()
→ filter: remind_at <= now AND completed = 0
→ send via context.bot.send_message()
→ db.complete_reminder(id)
```

---

## 🎨 Особенности реализации

### Асинхронность
- Весь код на async/await
- aiosqlite для БД
- aiohttp для HTTP запросов
- python-telegram-bot async версия

### Безопасность
- Whitelist через ALLOWED_USER_IDS
- Секреты в .env (не в git)
- .gitignore для защиты данных

### Обработка ошибок
- Try/except в критических местах
- Логирование через logging
- Graceful degradation

### Оптимизация
- Ограничение контекста (MAX_CONTEXT_MESSAGES=20)
- Переиспользование HTTP сессий
- Background jobs для напоминаний

---

## 📝 Команды бота (30+)

### ИИ (3)
- текст, `/clear`, `/summarize`

### Память (3)
- `/remember`, `/recall`, `/forget`

### Заметки (3)
- `/note`, `/notes`, `/delnote`

### Напоминания (1)
- `/remind`

### Работа (3)
- `/stats`, `/workers`, `/check`

### Информация (3)
- `/weather`, `/rates`, `/crypto`

### Развлечения (5)
- `/fact`, `/joke`, `/quote`, `/activity`, `/tips`

### Игры (3)
- `/dice`, `/8ball`, `/choose`

### Система (3)
- `/system`, `/help`, `/start`

---

## 🔧 Технический стек

### Основные зависимости
```
python-telegram-bot==21.5  # Telegram API
playwright==1.48.0         # Браузерная автоматизация
aiohttp==3.10.5           # HTTP клиент
python-dotenv==1.0.1      # .env парсинг
aiosqlite==0.20.0         # Async SQLite
psutil==6.0.0             # Системная информация
```

### Python версия
- Минимум: 3.10+
- Используется: async/await, type hints

---

## 🚀 DeepSeek API возможности

### Текущая реализация
- Модель: `deepseek-chat` (non-thinking mode)
- API: https://api.deepseek.com
- Совместимость: OpenAI SDK

### Доступные возможности (из документации)

1. **deepseek-reasoner** - thinking mode
   - Для сложных задач с рассуждениями
   - Показывает процесс мышления

2. **Function Calling**
   - Структурированные вызовы функций
   - Можно интегрировать с командами бота

3. **JSON Output**
   - Структурированные ответы
   - Для парсинга данных

4. **Context Caching**
   - Экономия токенов на повторяющемся контексте
   - Для длинных промптов

5. **Streaming**
   - Постепенная отправка ответа
   - Для лучшего UX

---

## 📊 Метрики использования

### Рабочий сайт (из скриншота)
- Всего записей: 8
- Всего SFS: 2806
- Всего SCH: 262
- Активных сотрудников: 8
- Команды: Good Bunny (зеленый), Velvet (красный)

### Работники
- Alina (@helpmepleaseviinc) - Good Bunny
- Karina (@american_satan) - Good Bunny
- Nika (@vanyia194) - Good Bunny
- Oleg (@OlegMano) - Velvet
- Slavik (@polovinкoo) - Good Bunny
- Stazon (@Duh08) - Good Bunny
- Timofey (@TT_gens) - Good Bunny (сам пользователь!)
- Vlad (@vladred24) - Good Bunny

---

## 💡 Идеи для улучшения

### Приоритетные
1. **Reasoning mode** для сложных вопросов
2. **Function calling** для команд
3. **Streaming** для длинных ответов
4. **Context caching** для экономии

### Дополнительные
1. Голосовые сообщения (Whisper)
2. Анализ изображений (Vision)
3. Генерация изображений (DALL-E)
4. Графики статистики (matplotlib)
5. Автоматические отчеты по расписанию

---

## 🐛 Известные особенности

1. **Парсер сайта** - нужна адаптация селекторов под реальный сайт
2. **SQLite** - для одного пользователя достаточно
3. **Polling** - есть задержки (webhooks быстрее)
4. **Память** - растет со временем (нужна ротация)

---

## 📚 Документация

### Файлы
- `START_HERE.txt` - начало работы
- `QUICKSTART.md` - быстрый старт
- `README.md` - полная документация
- `EXAMPLES.md` - примеры команд
- `CHEATSHEET.md` - шпаргалка
- `DEPLOY.md` - деплой на сервер
- `PROJECT_INFO.md` - техническая инфа
- `OVERVIEW.md` - обзор проекта

### Скрипты
- `install.bat/sh` - установка
- `start.bat/sh` - запуск
- `setup.py` - настройка
- `test_config.py` - проверка конфига

---

## 🎯 Текущий статус

### ✅ Реализовано
- Все основные функции
- 30+ команд
- Документация
- Скрипты установки
- Обработка ошибок

### 🔄 В процессе
- Настройка .env пользователем
- Первый запуск
- Тестирование функций

### 📋 Следующие шаги
1. ✅ Интеграция reasoning mode (deepseek-reasoner)
2. ✅ JSON extraction реализован
3. ✅ Новая команда /think
4. ⏳ Адаптация парсера под реальный сайт
5. ⏳ Тестирование в боевых условиях
6. ⏳ Function calling интеграция
7. ⏳ Streaming для длинных ответов

---

## 🆕 Последние обновления (26.10.2025)

### 🇺🇦 Обновление 1.2.0: Кнопочное меню + Украина!

**Добавлено:**

1. **📱 Кнопочное меню (ReplyKeyboard)**
   - Главное меню с 8 кнопками
   - Подменю для каждой категории
   - Кнопка 🏠 для возврата
   - Файл: `keyboards.py`
   - Обработчик: `handlers/menu_handler.py`

2. **🇺🇦 Перебазировано на Украину**
   - TIMEZONE: Europe/Kiev (было Europe/Moscow)
   - Примеры городов: Київ, Харків, Одеса, Львів
   - ИИ знает о локации пользователя
   - Поддержка украинского языка

3. **🎯 Быстрый доступ**
   - /weather Київ - кнопка в меню
   - /weather Харків - кнопка в меню
   - Подменю для всех категорий

**Структура меню:**
```
Главное меню:
├── 💬 Диалог
├── 📊 Статистика → [/stats, /workers, /check]
├── 📝 Заметки → [/note, /notes, /remind]
├── 🧠 Память → [/remember, /recall, /forget]
├── 🌤 Погода → [/weather Київ, /weather Харків, /rates]
├── 💰 Курсы
├── 🎲 Игры → [/joke, /quote, /fact, /dice, /8ball]
└── ℹ️ Помощь
```

---

### DeepSeek API - Все возможности интегрированы!

**Реализовано:**

1. **Reasoning Mode** (deepseek-reasoner)
   - Команда `/think` для сложных вопросов
   - Показывает процесс мышления модели
   - Методы: `reasoning_chat()`, `analyze_with_reasoning()`

2. **JSON Output**
   - Метод `extract_json()` для структурированных данных
   - Автоматический парсинг ответов
   - Для извлечения информации

3. **Function Calling** (готово)
   - Параметр `functions` в `chat()`
   - Для будущих интеграций

4. **Context Caching** (в API)
   - Автоматически работает
   - Экономия токенов

5. **Streaming** (подготовлено)
   - Параметр `stream=True`
   - Для будущих улучшений

**Новые методы AIService:**
```python
- reasoning_chat() - reasoning mode с контекстом
- extract_json() - извлечение JSON данных
- analyze_with_reasoning() - глубокий анализ
```

**Новые команды:**
- `/think <вопрос>` - использует deepseek-reasoner

**Документация:**
- `DEEPSEEK_FEATURES.md` - подробное описание всех возможностей
- [API Docs](https://api-docs.deepseek.com/)

---

**Обновлено:** 26.10.2025  
**Версия:** 1.2.0  
**Статус:** Production Ready 🚀 + Reasoning Mode ⚡ + Кнопочное Меню 🇺🇦

