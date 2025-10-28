"""
Главный файл Telegram ИИ-бота
"""
import asyncio
import logging
import sys
from datetime import datetime

# Фикс кодировки для Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

import config
from database import Database
from services import AIService, MemoryService
from services.extras_service import ExtrasService
from services.vision_service import VisionService
from services.agent_service import AIAgentService
from services.function_tools import FunctionExecutor
from services.work_parser_service import get_parser_service
from handlers.ai_handler import AIHandler
from handlers.work_handler import WorkHandler
from handlers.utils_handler import UtilsHandler
from handlers.extras_handler import ExtrasHandler
from handlers.menu_handler import MenuHandler
from handlers.image_handler import ImageHandler
from handlers.agent_handler import AgentHandler
from keyboards import get_main_menu

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Главный класс бота"""
    
    def __init__(self):
        self.db = Database(config.DATABASE_PATH)
        self.ai = AIService()
        self.memory = MemoryService(self.db, self.ai)
        self.parser = get_parser_service()  # Новый Playwright парсер
        self.extras = ExtrasService()
        self.vision = VisionService()
        
        # Function executor для агента
        self.function_executor = FunctionExecutor(
            db=self.db,
            memory_service=self.memory,
            extras_service=self.extras,
            parser_service=self.parser
        )
        
        # AI Агент
        self.agent = AIAgentService(self.db, self.ai, self.function_executor)
        
        # Инициализируем обработчики
        self.ai_handler = AIHandler(
            db=self.db, 
            ai=self.ai, 
            memory=self.memory,
            extras_service=self.extras,
            parser_service=self.parser,
            agent_service=self.agent  # Передаем агента для расширенной проактивности
        )
        self.work_handler = WorkHandler(self.db, self.parser)
        self.utils_handler = UtilsHandler(self.db, self.memory)
        self.extras_handler = ExtrasHandler(self.extras)
        self.menu_handler = MenuHandler()
        self.image_handler = ImageHandler(self.vision, self.ai)
        self.agent_handler = AgentHandler(self.agent)
        
        self.app = None
    
    def initialize(self):
        """Инициализация бота и БД"""
        logger.info("🚀 Инициализация бота...")
        
        # Проверяем конфиг
        config.validate_config()
        
        # Инициализируем БД синхронно
        import asyncio
        asyncio.run(self.db.init_db())
        logger.info("✅ База данных инициализирована")
        
        # Создаем приложение
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Регистрируем обработчики команд
        self._register_handlers()
        
        # Добавляем задачи, если job_queue доступна
        if self.app.job_queue:
            # Добавляем задачу проверки напоминаний
            self.app.job_queue.run_repeating(
                self.check_reminders,
                interval=60,
                first=10
            )
            
            # Добавляем задачу проверки AI агента
            self.app.job_queue.run_repeating(
                self.check_agent,
                interval=3600,  # Каждый час
                first=300  # Первая проверка через 5 минут
            )
            logger.info("✅ Job queue настроена")
        else:
            logger.warning("⚠️ Job queue недоступна - фоновые задачи отключены")
        
        logger.info("✅ Обработчики зарегистрированы")
        logger.info("✅ Бот готов к запуску!")
        logger.info(f"📝 Разрешенные пользователи: {config.ALLOWED_USER_IDS}")
    
    def _register_handlers(self):
        """Регистрирует все обработчики команд"""
        
        # Стартовая команда и помощь
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.utils_handler.help_command))
        
        # ИИ команды
        self.app.add_handler(CommandHandler("clear", self.ai_handler.clear_context_command))
        self.app.add_handler(CommandHandler("summarize", self.ai_handler.summarize_command))
        self.app.add_handler(CommandHandler("think", self.ai_handler.think_command))
        
        # Рабочие команды
        self.app.add_handler(CommandHandler("stats", self.work_handler.stats_command))
        self.app.add_handler(CommandHandler("workers", self.work_handler.workers_command))
        self.app.add_handler(CommandHandler("check", self.work_handler.check_worker_command))
        self.app.add_handler(CommandHandler("screenshot", self.work_handler.send_worker_screenshot))
        
        # Память
        self.app.add_handler(CommandHandler("remember", self.utils_handler.remember_command))
        self.app.add_handler(CommandHandler("recall", self.utils_handler.recall_command))
        self.app.add_handler(CommandHandler("forget", self.utils_handler.forget_command))
        
        # Заметки
        self.app.add_handler(CommandHandler("note", self.utils_handler.note_command))
        self.app.add_handler(CommandHandler("notes", self.utils_handler.notes_command))
        self.app.add_handler(CommandHandler("delnote", self.utils_handler.delete_note_command))
        
        # Напоминания
        self.app.add_handler(CommandHandler("remind", self.utils_handler.remind_command))
        
        # Система
        self.app.add_handler(CommandHandler("system", self.utils_handler.system_command))
        
        # Дополнительные функции - Информация
        self.app.add_handler(CommandHandler("weather", self.extras_handler.weather_command))
        self.app.add_handler(CommandHandler("rates", self.extras_handler.rates_command))
        self.app.add_handler(CommandHandler("crypto", self.extras_handler.crypto_command))
        
        # Дополнительные функции - Развлечения
        self.app.add_handler(CommandHandler("fact", self.extras_handler.fact_command))
        self.app.add_handler(CommandHandler("joke", self.extras_handler.joke_command))
        self.app.add_handler(CommandHandler("quote", self.extras_handler.quote_command))
        self.app.add_handler(CommandHandler("activity", self.extras_handler.activity_command))
        self.app.add_handler(CommandHandler("tips", self.extras_handler.tips_command))
        
        # Дополнительные функции - Игры
        self.app.add_handler(CommandHandler("dice", self.extras_handler.dice_command))
        self.app.add_handler(CommandHandler("8ball", self.extras_handler.ball8_command))
        self.app.add_handler(CommandHandler("choose", self.extras_handler.choose_command))
        
        # Обработчики изображений
        self.app.add_handler(CommandHandler("ocr", self.image_handler.ocr_command))
        self.app.add_handler(CommandHandler("describe", self.image_handler.describe_command))
        self.app.add_handler(CommandHandler("photo", self.image_handler.photo_help_command))
        
        # AI Агент
        self.app.add_handler(CommandHandler("agent_start", self.agent_handler.start_agent_command))
        self.app.add_handler(CommandHandler("agent_stop", self.agent_handler.stop_agent_command))
        self.app.add_handler(CommandHandler("agent_status", self.agent_handler.agent_status_command))
        self.app.add_handler(CommandHandler("agent_help", self.agent_handler.agent_help_command))
        self.app.add_handler(CommandHandler("smart_remind", self.agent_handler.smart_reminder))
        self.app.add_handler(CommandHandler("smart_note", self.agent_handler.smart_note))
        
        # Обработчик фото (ВАЖНО: добавляем ПЕРЕД обработчиком текста)
        self.app.add_handler(
            MessageHandler(
                filters.PHOTO & filters.User(user_id=config.ALLOWED_USER_IDS),
                self.image_handler.handle_photo
            )
        )
        
        # Обработчик обычных текстовых сообщений (ИИ диалоги)
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.User(user_id=config.ALLOWED_USER_IDS),
                self.ai_handler.handle_message
            )
        )
        
        # Обработчик ошибок
        self.app.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Создаем пользователя в БД
        await self.db.ensure_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )
        
        welcome_message = f"""👋 Привет, **{user.first_name}**!

Я твой личный ИИ-помощник. Могу помочь с:

• 💬 Общением и советами
• 🧠 Запоминанием важных фактов
• 📊 Статистикой с рабочего сайта
• 📝 Заметками и напоминаниями
• 🖥 Мониторингом системы

Используй кнопки меню внизу ⬇️ или пиши сообщения напрямую!
"""
        
        await update.message.reply_text(
            welcome_message, 
            parse_mode='Markdown',
            reply_markup=get_main_menu()
        )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"❌ Exception: {context.error}", exc_info=context.error)
        
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "😔 Произошла ошибка при обработке команды."
            )
    
    async def check_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверяет и отправляет напоминания (job)"""
        try:
            reminders = await self.db.get_pending_reminders()
            
            if reminders:
                logger.info(f"🔔 Найдено {len(reminders)} напоминаний для отправки")
            
            for reminder in reminders:
                try:
                    logger.info(f"📤 Отправка напоминания: {reminder['text']} → {reminder['user_id']}")
                    
                    await context.bot.send_message(
                        chat_id=reminder['user_id'],
                        text=f"⏰ **Напоминание!**\n\n{reminder['text']}",
                        parse_mode='Markdown'
                    )
                    
                    await self.db.complete_reminder(reminder['id'])
                    logger.info(f"✅ Напоминание {reminder['id']} отправлено и отмечено как выполненное")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки напоминания {reminder['id']}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки напоминаний: {e}")
    
    async def check_agent(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверяет нужны ли проактивные действия от AI агента (job)"""
        try:
            # Проверяем для всех разрешенных пользователей
            for user_id in config.ALLOWED_USER_IDS:
                try:
                    message = await self.agent.check_and_act(user_id)
                    
                    if message:
                        logger.info(f"🤖 AI Агент: отправляю сообщение пользователю {user_id}")
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        logger.info(f"✅ Сообщение от агента отправлено")
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки агента для пользователя {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки AI агента: {e}")
    
    def run(self):
        """Запускает бота"""
        try:
            # Создаем новый event loop для Windows
            if sys.platform == "win32":
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Запускаем polling (он сам управляет loop)
            self.app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except KeyboardInterrupt:
            logger.info("⚠️ Получен сигнал остановки")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        finally:
            logger.info("✅ Бот остановлен")
    
def main():
    """Главная функция"""
    # Фикс для Windows - используем ProactorEventLoop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    bot = TelegramBot()
    
    try:
        bot.initialize()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    main()

