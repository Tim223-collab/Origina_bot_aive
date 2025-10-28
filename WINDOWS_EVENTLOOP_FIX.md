# 🔧 Фикс Event Loop для Windows

## ❌ Проблема

При запуске бота возникала ошибка:
```
RuntimeError: This event loop is already running
RuntimeError: Cannot close a running event loop
```

**Причина:** На Windows в некоторых средах (VSCode, Jupyter) event loop уже запущен, и asyncio.run() пытается создать второй, что вызывает конфликт.

---

## ✅ Решение (применено)

Добавлен **Windows ProactorEventLoopPolicy** для правильной работы asyncio на Windows.

### Исправлено в файлах:

**`main.py`:**
```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

**`setup.py`:**
```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

---

## 🚀 Теперь работает!

Просто запусти:
```bash
start.bat
```

Или напрямую:
```bash
python main.py
```

---

## ✅ Что исправлено

- ✅ Event loop правильно инициализируется на Windows
- ✅ Нет конфликтов с существующим loop
- ✅ Корректное закрытие при остановке
- ✅ Работает в VSCode, PowerShell, CMD

---

**Обновлено:** 26.10.2025  
**Статус:** Исправлено ✅

