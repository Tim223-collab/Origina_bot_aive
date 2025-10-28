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
        /remind <минуты> <текст> - создает напоминание
        Пример: /remind 30 Проверить почту
        """
        user = update.effective_user
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "⏰ **Создать напоминание:**\n"
                "`/remind <минуты> <текст>`\n\n"
                "Примеры:\n"
                "`/remind 30 Проверить почту`\n"
                "`/remind 60 Созвониться с Иваном`\n"
                "`/remind 1 Тест` - тестовое напоминание",
                parse_mode='Markdown'
            )
            return
        
        try:
            minutes = int(context.args[0])
            text = " ".join(context.args[1:])
            
            # Используем UTC время (как в БД)
            from datetime import timezone
            remind_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            
            reminder_id = await self.db.add_reminder(user.id, text, remind_at)
            
            # Для отображения конвертируем в локальное время
            import pytz
            ukraine_tz = pytz.timezone('Europe/Kiev')
            local_time = remind_at.astimezone(ukraine_tz)
            
            await update.message.reply_text(
                f"⏰ Напомню через {minutes} минут!\n\n"
                f"📝 {text}\n"
                f"🕐 {local_time.strftime('%H:%M')} (Киев)\n"
                f"🆔 Напоминание #{reminder_id}",
                parse_mode='Markdown'
            )
            
            print(f"✅ Создано напоминание #{reminder_id}: {text} на {remind_at.isoformat()}")
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Первым аргументом должно быть число минут.")
    
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

