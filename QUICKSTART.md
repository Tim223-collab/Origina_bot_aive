# 🚀 Быстрый старт

## Установка (5 минут)

### Windows

```bash
# 1. Запустить установку
install.bat

# 2. Редактировать .env файл
notepad .env
```

### Linux/Mac

```bash
# 1. Дать права на выполнение
chmod +x install.sh

# 2. Запустить установку
./install.sh

# 3. Редактировать .env файл
nano .env
```

## Настройка .env

Открой `.env` и заполни:

```env
# Telegram (обязательно)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...  # От @BotFather
ALLOWED_USER_IDS=123456789            # От @userinfobot

# DeepSeek (обязательно)
DEEPSEEK_API_KEY=sk-...               # От platform.deepseek.com

# Рабочий сайт (опционально)
WORK_SITE_URL=https://your-site.com
WORK_SITE_USERNAME=your_username
WORK_SITE_PASSWORD=your_password
```

## Получение ключей

### 1. Telegram Bot Token (2 минуты)
1. Открой [@BotFather](https://t.me/botfather)
2. Напиши `/newbot`
3. Укажи имя и username бота
4. Скопируй токен

### 2. Твой Telegram ID (30 секунд)
1. Открой [@userinfobot](https://t.me/userinfobot)
2. Скопируй ID

### 3. DeepSeek API (3 минуты)
1. Зайди на [platform.deepseek.com](https://platform.deepseek.com)
2. Зарегистрируйся
3. Пополни баланс ($5 хватит на месяцы)
4. API Keys → Create API Key
5. Скопируй ключ

## Запуск

```bash
# Проверка настройки
python setup.py

# Запуск бота
python main.py
```

Готово! Напиши боту в Telegram `/start` 🎉

## Первые команды

- Просто напиши "Привет" - бот ответит
- `/help` - список всех команд
- `/weather Москва` - погода
- `/joke` - шутка
- `/remember personal имя Иван` - сохранить в память

## Проблемы?

### Ошибка: TELEGRAM_BOT_TOKEN не установлен
- Проверь что `.env` файл создан
- Проверь что токен правильно скопирован

### Ошибка: Playwright не настроен
```bash
playwright install chromium
```

### Бот не отвечает
- Проверь что твой ID в ALLOWED_USER_IDS
- Проверь что бот запущен (должно быть "✅ Бот запущен!")

## Что дальше?

1. **Настрой парсер сайта** - если нужно парсить рабочий сайт
2. **Используй память** - бот будет запоминать важное
3. **Создавай заметки** - `/note` для быстрых записей
4. **Ставь напоминания** - `/remind 30 Проверить почту`

## Полезные ссылки

- [Полная документация](README.md)
- [DeepSeek Platform](https://platform.deepseek.com)
- [Telegram Bot API](https://core.telegram.org/bots)

---

**Приятного использования! 🤖**

