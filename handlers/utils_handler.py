"""
Обработчики утилит: память, заметки, напоминания, система
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from datetime import datetime, timedelta
import psutil
import platform

from database import Database
from services import MemoryService


class UtilsHandler:
    def __init__(self, db: Database, memory: MemoryService):
        self.db = db
        self.memory = memory
    
    # === ПАМЯТЬ ===
    
    async def remember_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /remember <категория> <ключ> <значение>
        Пример: /remember personal день_рождения 15.05.1990
        """
        user = update.effective_user
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "💭 **Сохранить в память:**\n"
                "`/remember <категория> <ключ> <значение>`\n\n"
                "Пример:\n"
                "`/remember personal день_рождения 15.05.1990`\n"
                "`/remember work проект_дедлайн 31.12.2025`",
                parse_mode='Markdown'
            )
            return
        
        category = context.args[0]
        key = context.args[1]
        value = " ".join(context.args[2:])
        
        success = await self.memory.remember_fact(user.id, category, key, value)
        
        if success:
            await update.message.reply_text(
                f"✅ Запомнил!\n\n"
                f"📁 Категория: **{category}**\n"
                f"🔑 Ключ: **{key}**\n"
                f"📝 Значение: **{value}**",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Не удалось сохранить.")
    
    async def recall_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /recall [категория] - показывает сохраненные факты
        """
        user = update.effective_user
        
        category = context.args[0] if context.args else None
        
        memory_text = await self.memory.format_memory_for_display(user.id, category)
        
        await update.message.reply_text(memory_text, parse_mode='Markdown')
    
    async def forget_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /forget <категория> <ключ> - удаляет факт из памяти
        """
        user = update.effective_user
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "🗑 **Удалить из памяти:**\n"
                "`/forget <категория> <ключ>`\n\n"
                "Пример:\n"
                "`/forget personal день_рождения`",
                parse_mode='Markdown'
            )
            return
        
        category = context.args[0]
        key = context.args[1]
        
        success = await self.memory.forget_fact(user.id, category, key)
        
        if success:
            await update.message.reply_text(
                f"🗑 Удалено: {category} / {key}"
            )
        else:
            await update.message.reply_text("❌ Не удалось удалить.")
    
    # === ЗАМЕТКИ ===
    
    async def note_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /note <текст> - создает заметку
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "📝 **Создать заметку:**\n"
                "`/note <текст заметки>`\n\n"
                "Пример:\n"
                "`/note Не забыть купить молоко`"
            )
            return
        
        content = " ".join(context.args)
        
        note_id = await self.db.add_note(user.id, content)
        
        await update.message.reply_text(
            f"📝 Заметка сохранена! (ID: {note_id})"
        )
    
    async def notes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /notes [поиск] - показывает заметки
        """
        user = update.effective_user
        
        search = " ".join(context.args) if context.args else None
        
        notes = await self.db.get_notes(user.id, search)
        
        if not notes:
            await update.message.reply_text("📭 Заметок нет.")
            return
        
        message = f"📝 **Заметки** ({len(notes)}):\n\n"
        
        for note in notes[:10]:  # Показываем только первые 10
            date = datetime.fromisoformat(note['created_at']).strftime('%d.%m.%Y %H:%M')
            message += f"**#{note['id']}** _{date}_\n"
            message += f"{note['content'][:100]}\n\n"
        
        if len(notes) > 10:
            message += f"_...и еще {len(notes) - 10} заметок_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def delete_note_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /delnote <id> - удаляет заметку
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "🗑 **Удалить заметку:**\n"
                "`/delnote <ID>`"
            )
            return
        
        try:
            note_id = int(context.args[0])
            await self.db.delete_note(user.id, note_id)
            await update.message.reply_text(f"🗑 Заметка #{note_id} удалена.")
        except ValueError:
            await update.message.reply_text("❌ Неверный ID заметки.")
    
    # === НАПОМИНАНИЯ ===
    
    async def remind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /remind <минуты|время> <текст> - создает напоминание
        Поддерживает как минуты, так и естественный язык
        
        Примеры: 
        - /remind 30 Проверить почту
        - /remind завтра в 9 утра Встреча
        - /remind через 2 часа Позвонить
        """
        user = update.effective_user
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "⏰ <b>Создать напоминание:</b>\n"
                "<code>/remind &lt;время&gt; &lt;текст&gt;</code>\n\n"
                "<b>Примеры:</b>\n"
                "• <code>/remind 30 Проверить почту</code>\n"
                "• <code>/remind завтра в 9 утра Встреча</code>\n"
                "• <code>/remind через 2 часа Позвонить</code>\n"
                "• <code>/remind 23 октября в 14:00 День рождения</code>",
                parse_mode='HTML'
            )
            return
        
        try:
            # Пробуем распарсить как число минут (старый формат)
            minutes = int(context.args[0])
            text = " ".join(context.args[1:])
            
            # Используем UTC время (как в БД)
            from datetime import timezone
            remind_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            
        except ValueError:
            # Не число - используем AI для парсинга естественного языка
            full_text = " ".join(context.args)
            await update.message.reply_text("🤔 Анализирую время...")
            
            result = await self._parse_reminder_with_ai(full_text, user.id)
            
            if not result:
                await update.message.reply_text(
                    "❌ Не смог понять время. Попробуй:\n"
                    "• <code>/remind 30 текст</code> (минуты)\n"
                    "• <code>/remind завтра в 10:00 текст</code>\n"
                    "• <code>/remind через 2 часа текст</code>",
                    parse_mode='HTML'
                )
                return
            
            remind_at, text = result
        
        # Создаём напоминание
        reminder_id = await self.db.add_reminder(user.id, text, remind_at)
        
        # Для отображения конвертируем в локальное время
        import pytz
        ukraine_tz = pytz.timezone('Europe/Kiev')
        local_time = remind_at.astimezone(ukraine_tz)
        
        # Вычисляем разницу во времени
        now_ukraine = datetime.now(ukraine_tz)
        time_delta = local_time - now_ukraine
        
        if time_delta.days > 0:
            time_str = f"через {time_delta.days}д {time_delta.seconds // 3600}ч"
        elif time_delta.seconds >= 3600:
            time_str = f"через {time_delta.seconds // 3600}ч {(time_delta.seconds % 3600) // 60}мин"
        else:
            time_str = f"через {time_delta.seconds // 60}мин"
        
        await update.message.reply_text(
            f"⏰ <b>Напоминание создано!</b>\n\n"
            f"📝 {text}\n"
            f"🕐 {local_time.strftime('%d.%m.%Y %H:%M')} (Киев)\n"
            f"⏱ {time_str}\n"
            f"🆔 #{reminder_id}",
            parse_mode='HTML'
        )
        
        print(f"✅ Создано напоминание #{reminder_id}: {text} на {remind_at.isoformat()}")
    
    async def _parse_reminder_with_ai(self, text: str, user_id: int):
        """
        Парсит время из естественного языка через AI
        
        Returns:
            tuple: (datetime, текст_напоминания) или None
        """
        from datetime import timezone
        import pytz
        
        # Текущее время в Киеве для контекста
        ukraine_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(ukraine_tz)
        
        prompt = f"""Сейчас: {now.strftime('%d.%m.%Y %H:%M')} (Киев, Украина)
День недели: {now.strftime('%A')}

Пользователь написал: "{text}"

Извлеки:
1. Когда напомнить (дата и время)
2. Текст напоминания

Верни ТОЛЬКО JSON (без markdown):
{{
    "minutes_from_now": число_минут_от_текущего_времени,
    "reminder_text": "текст напоминания"
}}

Примеры:
- "завтра в 9 утра Встреча" → {{"minutes_from_now": 945, "reminder_text": "Встреча"}}
- "через 2 часа Позвонить" → {{"minutes_from_now": 120, "reminder_text": "Позвонить"}}
- "23 октября в 14:00 ДР" → {{"minutes_from_now": (рассчитай от текущего времени), "reminder_text": "ДР"}}

Если не можешь понять - верни {{"error": "причина"}}"""

        try:
            # Используем AI для парсинга
            messages = [
                {"role": "system", "content": "Ты парсишь время из естественного языка. Отвечай ТОЛЬКО JSON, без комментариев."},
                {"role": "user", "content": prompt}
            ]
            
            from services import AIService
            ai = AIService()
            response = await ai.chat(messages, temperature=0.2, max_tokens=100, json_mode=True)  # Оптимизация: 200→100
            
            if not response:
                return None
            
            import json
            result = json.loads(response)
            
            if "error" in result:
                print(f"❌ AI не смог распарсить время: {result['error']}")
                return None
            
            minutes = result.get("minutes_from_now")
            reminder_text = result.get("reminder_text")
            
            if not minutes or not reminder_text:
                return None
            
            # Вычисляем время напоминания в UTC
            remind_at = datetime.now(timezone.utc) + timedelta(minutes=int(minutes))
            
            return (remind_at, reminder_text)
            
        except Exception as e:
            print(f"❌ Ошибка парсинга времени через AI: {e}")
            return None
    
    # === СИСТЕМА ===
    
    async def system_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /system - показывает информацию о системе
        """
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Получаем информацию о системе
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        message = f"""🖥 **Информация о системе**

💻 **ОС:** {platform.system()} {platform.release()}
🔧 **Процессор:** {psutil.cpu_count()} ядер
📊 **Загрузка CPU:** {cpu_percent}%

💾 **Память:**
  • Всего: {memory.total / (1024**3):.1f} GB
  • Использовано: {memory.used / (1024**3):.1f} GB ({memory.percent}%)
  • Свободно: {memory.available / (1024**3):.1f} GB

💿 **Диск:**
  • Всего: {disk.total / (1024**3):.1f} GB
  • Использовано: {disk.used / (1024**3):.1f} GB ({disk.percent}%)
  • Свободно: {disk.free / (1024**3):.1f} GB

⏱ **Аптайм:** {uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /help - показывает список команд
        """
        help_text = """🤖 **Все команды AIVE**

━━━━━━━━━━━━━━━━━━━━━

**🤖 AI Агент (Проактивный):**
/agent_start - Включить агента
/agent_stop - Выключить агента  
/agent_status - Статус агента
/agent_help - Справка по агенту
/smart_remind - Умное напоминание
/smart_note - Умная заметка

**📸 Изображения:**
/ocr - Распознать текст
/describe - Описать фото
/photo - Справка по фото

**🧠 ИИ и диалоги:**
/clear - Очистить историю
/summarize - Резюме разговора
/think - Глубокий анализ

**💭 Память:**
/remember - Сохранить факт
/recall - Показать память
/forget - Удалить факт

**📝 Заметки:**
/note - Создать заметку
/notes - Показать заметки
/delnote - Удалить заметку

**⏰ Напоминания:**
/remind - Создать напоминание

**📊 Работа:**
/stats - Статистика с сайта
/workers - Список работников
/check - Проверить работника

**🌍 Информация:**
/weather - Погода
/rates - Курсы валют
/crypto - Крипто цена

**🎮 Развлечения:**
/fact - Интересный факт
/joke - Шутка
/quote - Мотивация
/activity - Чем заняться
/tips - Полезный совет

**🎲 Игры:**
/dice - Бросить кости
/8ball - Магический шар
/choose - Выбрать вариант

**🖥 Система:**
/system - Инфо о системе
/help - Эта справка

━━━━━━━━━━━━━━━━━━━━━

💡 **Просто пиши - я пойму!**

🤖 **AI Агент активен:**
• Извлекаю задачи из диалога
• Учусь на паттернах
• Предлагаю помощь
• Распознаю завершение задач

✨ **Отправь фото** - проанализирую
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

