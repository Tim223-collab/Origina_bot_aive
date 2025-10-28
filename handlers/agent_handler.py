"""
Обработчики AI Агента
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from services.agent_service import AIAgentService


class AgentHandler:
    """Управление AI агентом AIVE"""
    
    def __init__(self, agent_service: AIAgentService):
        self.agent = agent_service
    
    async def start_agent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /agent_start - Включить AI агента
        """
        user = update.effective_user
        
        self.agent.enable_agent(user.id)
        
        await update.message.reply_text(
            "🤖 **AIVE AI Агент активирован!**\n\n"
            "Теперь я буду:\n"
            "• 🌅 Присылать утренние сводки\n"
            "• 🌙 Делать вечерние отчеты\n"
            "• 💡 Проактивно предлагать помощь\n"
            "• 🔔 Умно напоминать о задачах\n"
            "• 📊 Мониторить твои дела\n\n"
            "**Команды:**\n"
            "• /agent_status - статус агента\n"
            "• /agent_stop - выключить агента\n\n"
            "💫 Я на страже твоих задач!",
            parse_mode='Markdown'
        )
    
    async def stop_agent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /agent_stop - Выключить AI агента
        """
        user = update.effective_user
        
        self.agent.disable_agent(user.id)
        
        await update.message.reply_text(
            "⏸️ **AI Агент приостановлен**\n\n"
            "Я буду ждать когда понадоблюсь снова.\n\n"
            "Чтобы включить обратно: /agent_start",
            parse_mode='Markdown'
        )
    
    async def agent_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /agent_status - Статус AI агента
        """
        user = update.effective_user
        
        status = self.agent.get_status(user.id)
        
        status_emoji = "🟢 Активен" if status['enabled'] else "🔴 Выключен"
        
        message = f"🤖 **Статус AI Агента AIVE**\n\n"
        message += f"**Состояние:** {status_emoji}\n\n"
        
        if status['enabled']:
            message += "**Возможности:**\n"
            for capability in status['capabilities']:
                message += f"• {capability}\n"
            
            if status['last_check']:
                last_check_str = status['last_check'].strftime('%H:%M')
                message += f"\n**Последняя проверка:** {last_check_str}\n"
            
            message += "\n**Управление:**\n"
            message += "• /agent_stop - выключить агента\n"
        else:
            message += "Агент в режиме ожидания.\n\n"
            message += "**Активировать:** /agent_start"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def agent_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /agent_help - Справка по AI агенту
        """
        
        help_text = """🤖 **AI Агент AIVE - Справка**

**Что это?**
Проактивный AI помощник, который работает автоматически и не ждёт твоих команд!

━━━━━━━━━━━━━━━━━━━━━

**🌅 Утренние сводки (7-9 утра)**
• Список напоминаний на день
• План задач
• Прогноз погоды

**🌙 Вечерние отчёты (20-21 час)**
• Что сделано за день
• Статистика активности
• Планы на завтра

**💡 Проактивные действия**
• Напоминает о забытых задачах
• Предлагает создать заметку
• Подсказывает полезные функции
• Мониторит рабочую статистику

**🔔 Умные напоминания**
• Понимает естественный язык
• "через час" → создаст на час вперёд
• "завтра утром" → на утро

**📝 Умные заметки**
• Автоматически добавляет теги
• Категоризирует информацию
• Структурирует данные

━━━━━━━━━━━━━━━━━━━━━

**Команды:**

• `/agent_start` - включить агента
• `/agent_stop` - выключить агента
• `/agent_status` - статус агента
• `/agent_help` - эта справка

━━━━━━━━━━━━━━━━━━━━━

**Примеры работы:**

**Ситуация 1: Утро**
```
AIVE: 🌅 Доброе утро! У тебя 3 напоминания на сегодня:
      1. Встреча с клиентом (14:00)
      2. Проверить почту (16:00)
      3. Позвонить Андрею (18:00)
      
      💪 Хорошего дня!
```

**Ситуация 2: В разговоре**
```
ТЫ: Мне нужно не забыть купить молоко

AIVE: 💡 Хочешь я создам напоминание об этом?

ТЫ: Да

AIVE: ✅ Создано напоминание "купить молоко" на 18:00
```

**Ситуация 3: Проактивность**
```
AIVE: 📊 Заметил что уже 14:00.
      Хочешь проверим статистику работы?
```

━━━━━━━━━━━━━━━━━━━━━

**💡 Совет:**
Агент ненавязчив! Пишет не чаще раза в час и только когда это действительно полезно.

**🎯 Лучшая практика:**
Включи агента и забудь о нём. Он сам будет помогать когда нужно!
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def smart_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /smart_remind [текст] - Умное напоминание
        
        Агент сам определит время из текста
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "📝 Использование: /smart_remind [что напомнить]\n\n"
                "Примеры:\n"
                "• `/smart_remind через час позвонить`\n"
                "• `/smart_remind завтра утром проверить почту`\n"
                "• `/smart_remind через 30 минут выйти`",
                parse_mode='Markdown'
            )
            return
        
        text = " ".join(context.args)
        
        await update.message.chat.send_action(ChatAction.TYPING)
        await update.message.reply_text("🤔 Определяю время...")
        
        result = await self.agent.smart_reminder(user.id, text)
        
        await update.message.reply_text(result)
    
    async def smart_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /smart_note [текст] - Умная заметка
        
        Агент сам добавит теги
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "📝 Использование: /smart_note [текст заметки]\n\n"
                "Я автоматически добавлю подходящие теги!\n\n"
                "Примеры:\n"
                "• `/smart_note Купить молоко и хлеб`\n"
                "• `/smart_note Встреча с клиентом завтра`\n"
                "• `/smart_note Выучить Python async/await`",
                parse_mode='Markdown'
            )
            return
        
        content = " ".join(context.args)
        
        await update.message.chat.send_action(ChatAction.TYPING)
        await update.message.reply_text("🏷️ Подбираю теги...")
        
        result = await self.agent.auto_categorize_note(user.id, content)
        
        await update.message.reply_text(result)
    
    async def check_proactive_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Проверяет нужна ли проактивная помощь при обычном сообщении
        Вызывается из ai_handler перед обработкой сообщения
        """
        user = update.effective_user
        message_text = update.message.text
        
        if not self.agent.is_enabled(user.id):
            return None
        
        # Проверяем нужна ли помощь
        suggestion = await self.agent.proactive_help(user.id, message_text)
        
        if suggestion:
            # Отправляем предложение (ненавязчиво, маленькое сообщение)
            await update.message.reply_text(
                f"💡 {suggestion}",
                reply_to_message_id=update.message.message_id
            )
        
        return suggestion

