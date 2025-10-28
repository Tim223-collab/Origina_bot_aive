"""
Обработчик кнопок меню
"""
from telegram import Update
from telegram.ext import ContextTypes

from keyboards import (
    get_main_menu,
    get_stats_menu,
    get_notes_menu,
    get_memory_menu,
    get_info_menu,
    get_games_menu
)


class MenuHandler:
    """Обработчик нажатий на кнопки меню"""
    
    async def handle_menu_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает нажатия на кнопки меню"""
        text = update.message.text
        
        # Главное меню
        if text == "🏠 Главное меню":
            await update.message.reply_text(
                "📱 Главное меню:",
                reply_markup=get_main_menu()
            )
            return True
        
        # Переход в подменю
        if text == "📊 Статистика":
            await update.message.reply_text(
                "📊 **Статистика работы**\n\n"
                "Выбери команду:",
                parse_mode='Markdown',
                reply_markup=get_stats_menu()
            )
            return True
        
        if text == "📝 Заметки":
            await update.message.reply_text(
                "📝 **Заметки и напоминания**\n\n"
                "Выбери команду:",
                parse_mode='Markdown',
                reply_markup=get_notes_menu()
            )
            return True
        
        if text == "🧠 Память":
            await update.message.reply_text(
                "🧠 **Долгосрочная память**\n\n"
                "Выбери команду:",
                parse_mode='Markdown',
                reply_markup=get_memory_menu()
            )
            return True
        
        if text == "🌤 Погода":
            await update.message.reply_text(
                "🌤 **Погода и курсы**\n\n"
                "Выбери город или команду:",
                parse_mode='Markdown',
                reply_markup=get_info_menu()
            )
            return True
        
        if text == "💬 Диалог":
            await update.message.reply_text(
                "💬 **Режим диалога**\n\n"
                "Просто пиши мне сообщения!\n\n"
                "Для сложных вопросов используй: `/think <вопрос>`\n"
                "Для очистки истории: `/clear`",
                parse_mode='Markdown',
                reply_markup=get_main_menu()
            )
            return True
        
        if text == "💰 Курсы":
            # Вызываем команду rates
            context.args = []
            from handlers.extras_handler import ExtrasHandler
            from services.extras_service import ExtrasService
            
            extras_service = ExtrasService()
            extras_handler = ExtrasHandler(extras_service)
            await extras_handler.rates_command(update, context)
            return True
        
        if text == "🎲 Игры":
            await update.message.reply_text(
                "🎲 **Игры и развлечения**\n\n"
                "Выбери команду:",
                parse_mode='Markdown',
                reply_markup=get_games_menu()
            )
            return True
        
        if text == "ℹ️ Помощь":
            # Показываем help
            from handlers.utils_handler import UtilsHandler
            from database import Database
            from services import MemoryService, AIService
            import config
            
            db = Database(config.DATABASE_PATH)
            ai = AIService()
            memory = MemoryService(db, ai)
            utils_handler = UtilsHandler(db, memory)
            
            await utils_handler.help_command(update, context)
            return True
        
        # Если не нажата кнопка меню, возвращаем False
        return False

