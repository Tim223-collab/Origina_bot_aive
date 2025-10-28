# 📝 Шпаргалка команд бота

## 🚀 Быстрый старт

```bash
# Установка (один раз)
install.bat              # Windows
./install.sh             # Linux/Mac

# Настройка .env
notepad .env             # Windows
nano .env                # Linux/Mac

# Проверка
python test_config.py

# Запуск
start.bat                # Windows
./start.sh               # Linux/Mac
python main.py           # Любая ОС
```

---

## 💬 ИИ Диалоги

| Команда | Описание | Пример |
|---------|----------|--------|
| (текст) | Обычное сообщение | Привет! Как дела? |
| `/clear` | Очистить историю | `/clear` |
| `/summarize` | Резюме разговора | `/summarize` |
| `/think <вопрос>` | **🆕 Reasoning mode** | `/think Как улучшить код?` |

**💡 /think** - использует deepseek-reasoner для сложных вопросов:
- Показывает процесс мышления
- Глубокий анализ
- Идеально для: код ревью, принятие решений, сложные задачи

---

## 🧠 Память

| Команда | Описание | Пример |
|---------|----------|--------|
| `/remember <категория> <ключ> <значение>` | Сохранить факт | `/remember personal др 15.05` |
| `/recall [категория]` | Показать память | `/recall` или `/recall work` |
| `/forget <категория> <ключ>` | Удалить факт | `/forget personal др` |

**Популярные категории:**
- `personal` - личное
- `work` - работа
- `preferences` - предпочтения
- `learning` - обучение

---

## 📝 Заметки

| Команда | Описание | Пример |
|---------|----------|--------|
| `/note <текст>` | Создать заметку | `/note Купить молоко` |
| `/notes [поиск]` | Показать заметки | `/notes` или `/notes проект` |
| `/delnote <id>` | Удалить заметку | `/delnote 5` |

---

## ⏰ Напоминания

| Команда | Описание | Пример |
|---------|----------|--------|
| `/remind <минуты> <текст>` | Напомнить | `/remind 30 Позвонить` |

---

## 📊 Работа

| Команда | Описание | Пример |
|---------|----------|--------|
| `/stats [дата]` | Статистика | `/stats` или `/stats 26.10.2025` |
| `/workers [команда]` | Список работников | `/workers` или `/workers Good Bunny` |
| `/check <имя>` | Проверить работника | `/check Timofey` |

---

## 🌍 Информация

| Команда | Описание | Пример |
|---------|----------|--------|
| `/weather [город]` | Погода | `/weather Москва` |
| `/rates` | Курсы валют | `/rates` |
| `/crypto [символ]` | Цена криптовалюты | `/crypto BTC` |

---

## 🎮 Развлечения

| Команда | Описание | Пример |
|---------|----------|--------|
| `/fact` | Интересный факт | `/fact` |
| `/joke` | Шутка | `/joke` |
| `/quote` | Мотивация | `/quote` |
| `/activity` | Чем заняться | `/activity` |
| `/tips [категория]` | Совет | `/tips productivity` |

**Категории для `/tips`:**
- `productivity` - продуктивность
- `health` - здоровье
- `coding` - программирование

---

## 🎲 Игры

| Команда | Описание | Пример |
|---------|----------|--------|
| `/dice [XdY]` | Бросить кости | `/dice 2d6` |
| `/8ball <вопрос>` | Магический шар | `/8ball Стоит ли учить Python?` |
| `/choose <А> или <Б>` | Выбрать вариант | `/choose пицца или суши` |

---

## 🖥 Система

| Команда | Описание | Пример |
|---------|----------|--------|
| `/system` | Инфо о системе | `/system` |
| `/help` | Список команд | `/help` |
| `/start` | Начало работы | `/start` |

---

## 📋 Категории памяти

```yaml
personal:
  - имя: Иван
  - день_рождения: 15.05.1990
  - город: Москва
  - увлечения: программирование

work:
  - должность: разработчик
  - проект: telegram-bot
  - дедлайн: 31.12.2025

preferences:
  - язык: Python
  - редактор: VSCode
  - кофе: черный без сахара

learning:
  - текущая_тема: Docker
  - цель: изучить за месяц
```

---

## 🎯 Типичные сценарии

### Планирование дня
```
/note План на день: встреча, отчет, код-ревью
/remind 60 Встреча с командой
/remind 180 Отправить отчет
```

### Изучение нового
```
Расскажи про Docker
/remember learning тема Docker
/note Docker: контейнеры, образы, docker-compose
```

### Проверка работы
```
/stats
/workers Good Bunny
/check Timofey
```

### Развлечение
```
/joke
/fact
/quote
/8ball Стоит ли мне выпить кофе?
```

---

## ⌨️ Горячие комбинации

Для быстрого доступа создай команды бота в Telegram:
1. Открой чат с @BotFather
2. Выбери своего бота
3. Edit Bot → Edit Commands
4. Вставь:

```
start - Начало работы
help - Список команд
clear - Очистить историю
stats - Статистика работы
weather - Погода
rates - Курсы валют
note - Создать заметку
notes - Показать заметки
remind - Напомнить
remember - Запомнить факт
recall - Показать память
joke - Рассказать шутку
quote - Мотивация
system - Инфо о системе
```

---

## 🔧 Настройка

### .env файл
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
ALLOWED_USER_IDS=123456789
DEEPSEEK_API_KEY=sk-...
WORK_SITE_URL=https://site.com
WORK_SITE_USERNAME=user
WORK_SITE_PASSWORD=pass
```

### Получение токенов

**Telegram Bot:**
→ @BotFather → `/newbot`

**Telegram ID:**
→ @userinfobot

**DeepSeek API:**
→ platform.deepseek.com → API Keys

---

## 🐛 Решение проблем

### Бот не отвечает
```bash
# Проверь конфигурацию
python test_config.py

# Проверь что бот запущен
# Проверь что твой ID в ALLOWED_USER_IDS
```

### Playwright ошибка
```bash
playwright install chromium
playwright install-deps chromium  # Linux
```

### База данных
```bash
# Бэкап
cp data/bot.db data/bot_backup.db

# Пересоздание
rm data/bot.db
python setup.py
```

---

## 📱 Деплой на сервер

### Быстрый способ (Screen)
```bash
screen -S bot
python3 main.py
# Ctrl+A, D - отключиться
screen -r bot  # вернуться
```

### Systemd Service
```bash
sudo cp bot.service /etc/systemd/system/telegram-bot.service
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

---

## 📊 Мониторинг

```bash
# Логи
journalctl -u telegram-bot -f

# Процесс
ps aux | grep main.py

# Ресурсы
top -p $(pgrep -f main.py)
```

---

**Сохрани эту шпаргалку для быстрого доступа! 📌**

