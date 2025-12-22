"""
Главный файл Telegram ИИ-бота
"""
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Фикс кодировки для Windows
if sys.platform == "win32":
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    except (AttributeError, OSError):
        # Если detach() не работает (например в IDE или systemd), 
        # полагаемся на UTF-8 по умолчанию в Python 3.7+
        pass

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
from services import HybridAIService, MemoryService, PersonalityService, ContentLibraryService
from services.extras_service import ExtrasService
from services.vision_service import VisionService
from services.agent_service import AIAgentService
from services.goals_service import GoalsService
from services.dtek_monitor_service import DTEKMonitorService
from services.function_tools import FunctionExecutor
from services.work_parser_service import get_parser_service
from handlers.ai_handler import AIHandler
from handlers.work_handler import WorkHandler
from handlers.utils_handler import UtilsHandler
from handlers.extras_handler import ExtrasHandler
from handlers.menu_handler import MenuHandler
from handlers.image_handler import ImageHandler
from handlers.agent_handler import AgentHandler
from handlers.content_handler import ContentHandler
from handlers.emotion_handler import EmotionHandler
from handlers.goals_handler import GoalsHandler
from handlers.dtek_handler import DTEKHandler
from keyboards import get_main_menu

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный instance бота для доступа из handlers
bot_instance = None


class TelegramBot:
    """Главный класс бота"""
    
    def __init__(self):
        global bot_instance
        bot_instance = self  # Сохраняем глобальный instance
        
        self.db = Database(config.DATABASE_PATH)
        self.ai = HybridAIService(db=self.db)  # 🎭 Гибридный AI с эмоциональным интеллектом
        self.memory = MemoryService(self.db, self.ai)
        self.parser = get_parser_service()  # Новый Playwright парсер
        self.extras = ExtrasService()
        self.vision = VisionService()
        
        # ДТЕК мониторинг отключений 🔌 (инициализируем ДО FunctionExecutor!)
        self.dtek = DTEKMonitorService(self.db)
        
        # Система целей и трекинга 🎯
        self.goals = GoalsService(self.db, self.ai)
        
        # Умная библиотека контента 📚✨
        self.content_library = ContentLibraryService(self.db, self.ai, self.vision)
        
        # Живая личность AIVE 🤖❤️
        self.personality = PersonalityService(self.db, self.ai, self.memory)
        
        # Function executor для агента (после всех сервисов!)
        self.function_executor = FunctionExecutor(
            db=self.db,
            memory_service=self.memory,
            extras_service=self.extras,
            parser_service=self.parser,
            dtek_service=self.dtek
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
            agent_service=self.agent,  # Передаем агента для расширенной проактивности
            personality_service=self.personality,  # Передаем личность для отслеживания активности
            function_executor=self.function_executor  # Передаем единый FunctionExecutor с ДТЕК
        )
        self.work_handler = WorkHandler(self.db, self.parser)
        self.utils_handler = UtilsHandler(self.db, self.memory)
        self.extras_handler = ExtrasHandler(self.extras)
        self.menu_handler = MenuHandler()
        self.image_handler = ImageHandler(self.vision, self.ai)
        self.agent_handler = AgentHandler(self.agent)
        self.content_handler = ContentHandler(self.db, self.content_library)
        
        # Эмоциональный интеллект 💙
        self.emotion_handler = EmotionHandler(self.ai.emotional)
        
        # Цели и трекинг 🎯
        self.goals_handler = GoalsHandler(self.goals)
        
        # ДТЕК мониторинг 🔌
        self.dtek_handler = DTEKHandler(self.dtek)
        
        self.app = None
    
    def initialize(self):
        """Инициализация бота и БД"""
        logger.info("🚀 Инициализация бота...")
        
        # Проверяем конфиг
        config.validate_config()
        
        # БД будет инициализирована асинхронно при запуске
        # НЕ используем asyncio.run() здесь - это создаёт вложенный event loop на Windows
        
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
            
            # Добавляем задачу проверки живой личности AIVE 🤖❤️
            self.app.job_queue.run_repeating(
                self.check_personality,
                interval=1800,  # Каждые 30 минут (с учетом рандома 20% = ~каждые 2.5 часа)
                first=600  # Первая проверка через 10 минут
            )
            logger.info("✅ Job queue настроена (напоминания, агент, личность)")
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
        
        # Библиотека контента 📚✨
        self.app.add_handler(CommandHandler("save", self.content_handler.handle_save_request))
        self.app.add_handler(CommandHandler("find", self.content_handler.find_command))
        self.app.add_handler(CommandHandler("library", self.content_handler.library_command))
        self.app.add_handler(CommandHandler("categories", self.content_handler.categories_command))
        
        # Эмоциональный интеллект 💙
        self.app.add_handler(CommandHandler("emotion", self.emotion_handler.emotion_status))
        self.app.add_handler(CommandHandler("test_emotion", self.emotion_handler.test_emotion))
        
        # Цели и трекинг 🎯
        self.app.add_handler(CommandHandler("goal", self.goals_handler.create_goal_command))
        self.app.add_handler(CommandHandler("goals", self.goals_handler.goals_list_command))
        self.app.add_handler(CommandHandler("goal_progress", self.goals_handler.goal_progress_command))
        self.app.add_handler(CommandHandler("goal_complete", self.goals_handler.goal_complete_command))
        self.app.add_handler(CommandHandler("goal_details", self.goals_handler.goal_details_command))
        self.app.add_handler(CommandHandler("goal_pause", self.goals_handler.goal_pause_command))
        self.app.add_handler(CommandHandler("goal_resume", self.goals_handler.goal_resume_command))
        self.app.add_handler(CommandHandler("goals_stats", self.goals_handler.goals_stats_command))
        
        # ДТЕК мониторинг 🔌
        self.app.add_handler(CommandHandler("dtek_setup", self.dtek_handler.setup_command))
        self.app.add_handler(CommandHandler("dtek_now", self.dtek_handler.check_now_command))
        self.app.add_handler(CommandHandler("dtek_today", self.dtek_handler.today_schedule_command))
        self.app.add_handler(CommandHandler("dtek_week", self.dtek_handler.week_schedule_command))
        self.app.add_handler(CommandHandler("dtek_monitor_start", self.dtek_handler.start_monitor_command))
        self.app.add_handler(CommandHandler("dtek_monitor_stop", self.dtek_handler.stop_monitor_command))
        self.app.add_handler(CommandHandler("dtek_monitor_status", self.dtek_handler.monitor_status_command))
        
        # Callback handlers для библиотеки контента
        from telegram.ext import CallbackQueryHandler
        self.app.add_handler(CallbackQueryHandler(
            self.content_handler.handle_title_callback,
            pattern="^content_"
        ))
        
        # Callback для автосохранения
        self.app.add_handler(CallbackQueryHandler(
            self.content_handler.handle_autosave_callback,
            pattern="^autosave_"
        ))
        
        # Обработчик фото (ВАЖНО: сначала проверяем библиотеку контента, потом image_handler)
        # Сначала библиотека контента (если в режиме сохранения)
        self.app.add_handler(
            MessageHandler(
                filters.PHOTO & filters.User(user_id=config.ALLOWED_USER_IDS),
                self._handle_photo_router  # Роутер который решает куда передать
            )
        )
        
        # Обработчик документов для библиотеки
        self.app.add_handler(
            MessageHandler(
                filters.Document.ALL & filters.User(user_id=config.ALLOWED_USER_IDS),
                self._handle_document_router
            )
        )
        
        # Обработчик обычных текстовых сообщений (сначала проверка библиотеки, потом ИИ)
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.User(user_id=config.ALLOWED_USER_IDS),
                self._handle_text_router
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
    
    async def _handle_photo_router(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Роутер для фото - решает куда передать (библиотека или image_handler)
        """
        # Проверяем режим сохранения или пользовательский заголовок
        if context.user_data.get('waiting_for_content') or context.user_data.get('waiting_for_custom_title'):
            # Передаем в библиотеку контента
            saved = await self.content_handler.handle_image_for_library(update, context)
            if saved:
                return  # Обработано
        
        # Иначе передаем в обычный image_handler
        await self.image_handler.handle_photo(update, context)
        
        # После обработки - проверяем нужно ли автосохранить
        photo = update.message.photo[-1]
        caption = update.message.caption or ""
        
        # Скачиваем фото для анализа и сохранения
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # Сохраняем изображение на диск для постоянного хранения
        images_dir = config.DATA_DIR / "images"
        images_dir.mkdir(exist_ok=True)
        file_name = f"{update.effective_user.id}_{int(time.time())}.jpg"
        file_path = images_dir / file_name
        file_path.write_bytes(image_bytes)
        
        # Принудительно сохраняем фото в БД (автосохранение)
        try:
            from services.content_library_service import ContentLibraryService
            content_service = ContentLibraryService(self.db, self.ai, self.vision)
            
            # Анализируем и сохраняем фото
            content_id, analysis = await content_service.analyze_and_save(
                user_id=update.effective_user.id,
                content_type="image",
                file_id=photo.file_id,
                file_path=str(file_path),
                image_bytes=bytes(image_bytes)
            )
            print(f"✅ Фото автосохранено в БД: ID={content_id}, title={analysis.get('suggested_title')}")
        except Exception as e:
            print(f"❌ Ошибка автосохранения фото: {e}")
        
        # Показываем предложение (если нужно)
        suggested = await self.content_handler.auto_suggest_save(
            update, context,
            content_type="image",
            caption=caption,
            file_id=photo.file_id,
            file_path=str(file_path),
            image_bytes=bytes(image_bytes)
        )
        # Если предложение показано - всё, иначе продолжаем обычную обработку
    
    async def _handle_document_router(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Роутер для документов - решает куда передать
        """
        # Проверяем режим сохранения
        if context.user_data.get('waiting_for_content'):
            saved = await self.content_handler.handle_document_for_library(update, context)
            if saved:
                return  # Обработано
        
        # Автопредложение сохранения документов
        document = update.message.document
        suggested = await self.content_handler.auto_suggest_save(
            update, context,
            content_type="document",
            file_name=document.file_name,
            file_id=document.file_id
        )
        
        if not suggested:
            # Если не предложили сохранить - показываем обычное сообщение
            await update.message.reply_text(
                "📄 Получил документ!\n\n"
                "Чтобы сохранить в библиотеку, используй /save и отправь документ заново."
            )
    
    async def _handle_text_router(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Роутер для текста - решает куда передать (библиотека или AI)
        """
        # Проверяем пользовательский заголовок
        if context.user_data.get('waiting_for_custom_title'):
            saved = await self.content_handler.handle_custom_title(update, context)
            if saved:
                return  # Обработано
        
        # Проверяем режим сохранения или автосохранение ссылок
        text = update.message.text
        url = self.content_handler.extract_url_from_text(text)
        
        if context.user_data.get('waiting_for_content'):
            if url:
                # Сохраняем как ссылку
                saved = await self.content_handler.handle_link_for_library(update, context, url)
                if saved:
                    return
            else:
                # Сохраняем как текст/код
                saved = await self.content_handler.handle_text_for_library(update, context)
                if saved:
                    return
        
        # Автопредложение для длинных текстов или ссылок
        if url:
            # Предлагаем сохранить ссылку
            suggested = await self.content_handler.auto_suggest_save(
                update, context,
                content_type="link",
                text=text,
                url=url
            )
            if suggested:
                return  # Показали предложение, не передаем в AI
        
        elif len(text) > 200:
            # Длинный текст - может быть важным
            suggested = await self.content_handler.auto_suggest_save(
                update, context,
                content_type="text",
                text=text,
                text_content=text
            )
            # Даже если предложили сохранить, продолжаем обработку через AI
        
        # Передаем в обычный AI handler
        await self.ai_handler.handle_message(update, context)
    
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
    
    async def check_personality(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверяет нужно ли отправить живое спонтанное сообщение (job)"""
        try:
            import random
            
            # Проверяем для всех разрешенных пользователей
            for user_id in config.ALLOWED_USER_IDS:
                try:
                    # Рандомный шанс 20% отправить сообщение (чтобы не спамить)
                    if random.random() > 0.2:
                        continue
                    
                    # Проверяем неактивность
                    inactivity_msg = await self.personality.generate_inactivity_message(user_id)
                    if inactivity_msg:
                        logger.info(f"💭 AIVE (неактивность): отправляю сообщение пользователю {user_id}")
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=inactivity_msg
                        )
                        logger.info(f"✅ Сообщение о неактивности отправлено")
                        continue
                    
                    # Генерируем спонтанное сообщение
                    spontaneous_msg = await self.personality.generate_spontaneous_message(user_id)
                    if spontaneous_msg:
                        logger.info(f"💭 AIVE (спонтанное): отправляю сообщение пользователю {user_id}")
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=spontaneous_msg
                        )
                        logger.info(f"✅ Спонтанное сообщение отправлено")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки личности для пользователя {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки личности AIVE: {e}")
    
    def run(self):
        """Запускает бота"""
        try:
            # Инициализируем БД асинхронно перед запуском
            async def init_db_async():
                await self.db.init_db()
                logger.info("✅ База данных инициализирована")
            
            # Получаем существующий event loop или создаём новый
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Инициализируем БД
            loop.run_until_complete(init_db_async())
            
            # Запускаем polling (он сам управляет event loop)
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

