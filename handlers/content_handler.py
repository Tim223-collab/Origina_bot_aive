"""
Обработчик умной библиотеки контента
Сохраняет все что отправляет пользователь с AI категоризацией
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from typing import Optional, Dict
import re

from database import Database
from services.content_library_service import ContentLibraryService


# Состояния диалога
WAITING_FOR_TITLE = 1


class ContentHandler:
    """
    Обрабатывает входящий контент и сохраняет в библиотеку
    """
    
    def __init__(self, db: Database, content_service: ContentLibraryService):
        self.db = db
        self.content = content_service
        
        # Временное хранилище для ожидания названия
        self.pending_content = {}  # {user_id: {content_data, analysis}}
    
    async def handle_save_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Команда /save для сохранения следующего контента
        """
        user = update.effective_user
        
        await update.message.reply_text(
            "💾 <b>Режим сохранения активирован!</b>\n\n"
            "Отправь мне:\n"
            "• 🖼️ Изображение (карта, скриншот, фото)\n"
            "• 📝 Текст или код\n"
            "• 🔗 Ссылку (YouTube, статья, и т.д.)\n"
            "• 📄 Документ\n"
            "• 🎵 Аудио\n"
            "• 🎬 Видео\n\n"
            "Я автоматически определю что это и предложу категорию!",
            parse_mode='HTML'
        )
        
        # Устанавливаем флаг ожидания контента
        context.user_data['waiting_for_content'] = True
    
    async def handle_image_for_library(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Обрабатывает изображение для библиотеки
        
        Returns:
            True если изображение сохранено, False если нужна дальнейшая обработка
        """
        user = update.effective_user
        
        # Проверяем режим сохранения или автосохранение
        if not context.user_data.get('waiting_for_content'):
            return False  # Не сохраняем, пусть обрабатывает image_handler
        
        # Убираем флаг ожидания
        context.user_data.pop('waiting_for_content', None)
        
        await update.message.chat.send_action(ChatAction.TYPING)
        await update.message.reply_text("🔍 Анализирую изображение...")
        
        # Получаем изображение
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # Анализируем и получаем предложение от AI
        content_id, analysis = await self.content.analyze_and_save(
            user_id=user.id,
            content_type="image",
            file_id=photo.file_id,
            image_bytes=bytes(image_bytes)
        )
        
        # Сохраняем в pending для запроса названия
        self.pending_content[user.id] = {
            'content_id': content_id,
            'analysis': analysis
        }
        
        # Спрашиваем название
        await self._ask_for_title(update, analysis)
        
        return True  # Обработано
    
    async def handle_text_for_library(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Обрабатывает текст для библиотеки
        
        Returns:
            True если текст сохранен, False если нужна дальнейшая обработка
        """
        user = update.effective_user
        text = update.message.text
        
        # Проверяем режим сохранения
        if not context.user_data.get('waiting_for_content'):
            # Автоопределение: длинный текст или код
            if len(text) < 100:
                return False  # Короткий текст - обычное сообщение
        
        # Убираем флаг
        context.user_data.pop('waiting_for_content', None)
        
        await update.message.chat.send_action(ChatAction.TYPING)
        await update.message.reply_text("🔍 Анализирую текст...")
        
        # Определяем это текст или код
        content_type = "text"  # AI сам определит в analyze_and_save
        
        # Анализируем и сохраняем
        content_id, analysis = await self.content.analyze_and_save(
            user_id=user.id,
            content_type=content_type,
            text_content=text
        )
        
        # Обновляем тип если AI определил что это код
        if analysis.get('content_type') == 'code':
            await self.db.update_content(content_id, user.id, metadata={'content_type': 'code'})
        
        # Сохраняем в pending
        self.pending_content[user.id] = {
            'content_id': content_id,
            'analysis': analysis
        }
        
        # Спрашиваем название
        await self._ask_for_title(update, analysis)
        
        return True
    
    async def handle_document_for_library(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает документ для библиотеки"""
        user = update.effective_user
        
        if not context.user_data.get('waiting_for_content'):
            return False
        
        context.user_data.pop('waiting_for_content', None)
        
        document = update.message.document
        file_name = document.file_name
        
        await update.message.reply_text("📄 Сохраняю документ...")
        
        # Сохраняем
        content_id, analysis = await self.content.analyze_and_save(
            user_id=user.id,
            content_type="document",
            file_id=document.file_id,
            file_name=file_name,
            metadata={'mime_type': document.mime_type, 'file_size': document.file_size}
        )
        
        analysis['suggested_title'] = file_name or "Документ"
        
        self.pending_content[user.id] = {
            'content_id': content_id,
            'analysis': analysis
        }
        
        await self._ask_for_title(update, analysis)
        
        return True
    
    async def handle_link_for_library(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> bool:
        """
        Обрабатывает ссылку для библиотеки
        
        Args:
            url: Извлеченный URL из сообщения
        """
        user = update.effective_user
        
        if not context.user_data.get('waiting_for_content'):
            # Автосохранение ссылок можно включить позже
            return False
        
        context.user_data.pop('waiting_for_content', None)
        
        await update.message.reply_text("🔗 Анализирую ссылку...")
        
        # Анализируем и сохраняем
        content_id, analysis = await self.content.analyze_and_save(
            user_id=user.id,
            content_type="link",
            url=url
        )
        
        self.pending_content[user.id] = {
            'content_id': content_id,
            'analysis': analysis
        }
        
        await self._ask_for_title(update, analysis)
        
        return True
    
    async def _ask_for_title(self, update: Update, analysis: Dict):
        """
        Спрашивает название для контента с предложением от AI
        """
        suggested_title = analysis.get('suggested_title', 'Без названия')
        category = analysis.get('category', 'other')
        description = analysis.get('description', '')
        
        # Эмодзи категории
        category_emoji = self.content.CATEGORIES.get(category, "📂").split()[0]
        
        # Создаем кнопки
        keyboard = [
            [InlineKeyboardButton("✅ Принять предложение", callback_data=f"content_accept_{suggested_title}")],
            [InlineKeyboardButton("✏️ Изменить название", callback_data="content_edit_title")],
            [InlineKeyboardButton("🔄 Другая категория", callback_data="content_change_category")],
            [InlineKeyboardButton("❌ Отменить", callback_data="content_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"✨ <b>Контент проанализирован!</b>\n\n"
            f"📝 <b>Описание:</b> {description}\n"
            f"{category_emoji} <b>Категория:</b> {category.title()}\n"
            f"💡 <b>Предложенное название:</b>\n<code>{suggested_title}</code>\n\n"
            f"Как сохраняем?"
        )
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def handle_title_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает кнопки подтверждения названия"""
        query = update.callback_query
        user = update.effective_user
        data = query.data
        
        await query.answer()
        
        if data.startswith("content_accept_"):
            # Принимаем предложенное название
            title = data.replace("content_accept_", "")
            
            if user.id in self.pending_content:
                content_id = self.pending_content[user.id]['content_id']
                
                # Обновляем запись
                await self.db.update_content(
                    content_id=content_id,
                    user_id=user.id,
                    title=title
                )
                
                await query.edit_message_text(
                    f"✅ <b>Сохранено!</b>\n\n"
                    f"📝 Название: <code>{title}</code>\n"
                    f"🆔 ID: #{content_id}\n\n"
                    f"Теперь могу найти по команде:\n"
                    f"<code>/find {title[:20]}</code>",
                    parse_mode='HTML'
                )
                
                self.pending_content.pop(user.id, None)
        
        elif data == "content_edit_title":
            # Ожидаем ввод нового названия
            context.user_data['waiting_for_custom_title'] = True
            
            await query.edit_message_text(
                "✏️ <b>Введи название:</b>\n\n"
                "Напиши как ты хочешь назвать этот контент.\n"
                "Например: <code>Карта метро Киева</code>",
                parse_mode='HTML'
            )
        
        elif data == "content_change_category":
            # Показываем список категорий
            keyboard = []
            for cat_key, cat_name in self.content.CATEGORIES.items():
                keyboard.append([InlineKeyboardButton(cat_name, callback_data=f"content_cat_{cat_key}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🔄 <b>Выбери категорию:</b>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        elif data.startswith("content_cat_"):
            # Выбрана новая категория
            new_category = data.replace("content_cat_", "")
            
            if user.id in self.pending_content:
                self.pending_content[user.id]['analysis']['category'] = new_category
                
                content_id = self.pending_content[user.id]['content_id']
                await self.db.update_content(
                    content_id=content_id,
                    user_id=user.id,
                    category=new_category
                )
                
                # Возвращаемся к вопросу о названии
                await self._ask_for_title_after_category(query, self.pending_content[user.id]['analysis'])
        
        elif data == "content_cancel":
            # Отмена сохранения
            if user.id in self.pending_content:
                content_id = self.pending_content[user.id]['content_id']
                await self.db.delete_content(content_id, user.id)
                self.pending_content.pop(user.id, None)
            
            await query.edit_message_text(
                "❌ Сохранение отменено.",
                parse_mode='HTML'
            )
    
    async def handle_custom_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает пользовательское название"""
        user = update.effective_user
        
        if not context.user_data.get('waiting_for_custom_title'):
            return False
        
        context.user_data.pop('waiting_for_custom_title', None)
        
        custom_title = update.message.text.strip()
        
        if user.id in self.pending_content:
            content_id = self.pending_content[user.id]['content_id']
            category = self.pending_content[user.id]['analysis'].get('category', 'other')
            
            # Обновляем запись
            await self.db.update_content(
                content_id=content_id,
                user_id=user.id,
                title=custom_title
            )
            
            category_emoji = self.content.CATEGORIES.get(category, "📂").split()[0]
            
            await update.message.reply_text(
                f"✅ <b>Сохранено!</b>\n\n"
                f"📝 Название: <code>{custom_title}</code>\n"
                f"{category_emoji} Категория: {category.title()}\n"
                f"🆔 ID: #{content_id}\n\n"
                f"Теперь могу найти по команде:\n"
                f"<code>/find {custom_title[:20]}</code>",
                parse_mode='HTML'
            )
            
            self.pending_content.pop(user.id, None)
        
        return True
    
    async def _ask_for_title_after_category(self, query, analysis: Dict):
        """Повторно спрашивает название после смены категории"""
        suggested_title = analysis.get('suggested_title', 'Без названия')
        category = analysis.get('category', 'other')
        
        category_emoji = self.content.CATEGORIES.get(category, "📂").split()[0]
        
        keyboard = [
            [InlineKeyboardButton("✅ Принять", callback_data=f"content_accept_{suggested_title}")],
            [InlineKeyboardButton("✏️ Изменить", callback_data="content_edit_title")],
            [InlineKeyboardButton("❌ Отменить", callback_data="content_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✨ <b>Категория обновлена!</b>\n\n"
            f"{category_emoji} <b>Категория:</b> {category.title()}\n"
            f"💡 <b>Название:</b> <code>{suggested_title}</code>\n\n"
            f"Как сохраняем?",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def find_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Команда /find для поиска в библиотеке
        
        Примеры:
        - /find карта метро
        - /find смешные видео
        - /find код по API
        """
        user = update.effective_user
        
        if not context.args:
            # Показываем статистику библиотеки
            stats = await self.content.get_library_stats(user.id)
            await update.message.reply_text(
                stats + "\n\n"
                "🔍 <b>Поиск:</b>\n"
                "<code>/find карта метро</code>\n"
                "<code>/find смешные видео</code>\n"
                "<code>/find код по API</code>",
                parse_mode='HTML'
            )
            return
        
        query = " ".join(context.args)
        
        await update.message.reply_text(f"🔍 Ищу: <i>{query}</i>...", parse_mode='HTML')
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Умный поиск через AI
        results = await self.content.smart_search(user.id, query)
        
        if not results:
            await update.message.reply_text(
                f"😔 Ничего не нашла по запросу: <i>{query}</i>\n\n"
                f"Попробуй:\n"
                f"• Другие ключевые слова\n"
                f"• Проверить категорию (<code>/categories</code>)\n"
                f"• Посмотреть всю библиотеку (<code>/library</code>)",
                parse_mode='HTML'
            )
            return
        
        # Отправляем результаты
        await update.message.reply_text(
            f"✅ Найдено: <b>{len(results)}</b>",
            parse_mode='HTML'
        )
        
        for item in results[:10]:  # Топ 10 результатов
            await self._send_content_item(update, context, item)
    
    async def _send_content_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item: Dict):
        """Отправляет элемент контента пользователю"""
        
        content_type = item['content_type']
        title = item.get('title') or 'Без названия'
        description = item.get('description', '')
        category = item.get('category', 'other')
        
        category_emoji = self.content.CATEGORIES.get(category, "📂").split()[0]
        
        caption = (
            f"📝 <b>{title}</b>\n"
            f"{category_emoji} {category.title()}\n"
            f"🆔 ID: #{item['id']}"
        )
        
        if description:
            caption += f"\n\n{description[:200]}"
        
        # Отправляем контент по типу
        if content_type == "image" and item.get('file_id'):
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=item['file_id'],
                caption=caption,
                parse_mode='HTML'
            )
        
        elif content_type == "text" and item.get('text_content'):
            text = item['text_content']
            await update.message.reply_text(
                f"{caption}\n\n"
                f"<code>{text[:1000]}</code>",
                parse_mode='HTML'
            )
        
        elif content_type == "code" and item.get('text_content'):
            code = item['text_content']
            await update.message.reply_text(
                f"{caption}\n\n"
                f"```\n{code[:1000]}\n```",
                parse_mode='Markdown'
            )
        
        elif content_type == "link" and item.get('url'):
            await update.message.reply_text(
                f"{caption}\n\n"
                f"🔗 {item['url']}",
                parse_mode='HTML'
            )
        
        elif content_type == "document" and item.get('file_id'):
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=item['file_id'],
                caption=caption,
                parse_mode='HTML'
            )
        
        else:
            await update.message.reply_text(caption, parse_mode='HTML')
    
    async def library_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /library для просмотра всей библиотеки"""
        user = update.effective_user
        
        stats = await self.content.get_library_stats(user.id)
        await update.message.reply_text(stats, parse_mode='HTML')
    
    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /categories для просмотра категорий"""
        user = update.effective_user
        
        categories = await self.db.get_categories(user.id)
        
        if not categories:
            await update.message.reply_text(
                "📂 Пока нет категорий.\n\nСохрани что-нибудь командой /save!"
            )
            return
        
        text = "📂 <b>Твои категории:</b>\n\n"
        
        for cat in categories:
            emoji = self.content.CATEGORIES.get(cat, "📂").split()[0]
            count = len(await self.db.get_content(user.id, category=cat, limit=1000))
            text += f"{emoji} <code>{cat}</code> — {count} элементов\n"
        
        text += "\n🔍 Найти по категории:\n<code>/find полезное</code>"
        
        await update.message.reply_text(text, parse_mode='HTML')
    
    def extract_url_from_text(self, text: str) -> Optional[str]:
        """Извлекает URL из текста"""
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        return match.group(0) if match else None
    
    async def auto_suggest_save(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        content_type: str,
        **kwargs
    ) -> bool:
        """
        Автоматически предлагает сохранить контент если AI считает что это нужно
        
        Args:
            content_type: Тип контента
            **kwargs: Параметры для should_auto_save
            
        Returns:
            True если предложение показано, False если нет
        """
        user = update.effective_user
        
        # AI определяет нужно ли сохранять
        decision = await self.content.should_auto_save(content_type, **kwargs)
        
        # Если confidence < 0.6 - не предлагаем
        if not decision.get('should_save') or decision.get('confidence', 0) < 0.6:
            return False
        
        # Сохраняем контекст для последующего сохранения
        context.user_data['auto_save_pending'] = {
            'content_type': content_type,
            'kwargs': kwargs
        }
        
        # Показываем кнопки
        keyboard = [
            [
                InlineKeyboardButton("💾 Сохранить", callback_data="autosave_yes"),
                InlineKeyboardButton("❌ Игнорировать", callback_data="autosave_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        reason = decision.get('reason', 'похоже на важную информацию')
        
        await update.message.reply_text(
            f"💡 Заметила что ты отправил {reason}.\n\n"
            f"Сохранить в библиотеку?",
            reply_markup=reply_markup
        )
        
        return True
    
    async def handle_autosave_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает кнопки автосохранения"""
        query = update.callback_query
        user = update.effective_user
        
        await query.answer()
        
        if query.data == "autosave_yes":
            # Пользователь хочет сохранить
            pending = context.user_data.get('auto_save_pending')
            
            if not pending:
                await query.edit_message_text("❌ Время истекло, отправь заново.")
                return
            
            await query.edit_message_text("🔍 Анализирую...")
            
            # Запускаем полный процесс сохранения
            content_id, analysis = await self.content.analyze_and_save(
                user_id=user.id,
                content_type=pending['content_type'],
                **pending['kwargs']
            )
            
            # Сохраняем в pending для запроса названия
            self.pending_content[user.id] = {
                'content_id': content_id,
                'analysis': analysis
            }
            
            # Создаем новое сообщение с запросом названия
            await query.message.reply_text("✨ Контент проанализирован!")
            
            # Используем существующий метод для запроса названия
            # Создаем фейковый update для _ask_for_title
            await self._ask_for_title_after_autosave(query, analysis)
            
            # Очищаем pending
            context.user_data.pop('auto_save_pending', None)
        
        elif query.data == "autosave_no":
            # Пользователь отказался
            await query.edit_message_text("👌 Хорошо, не буду сохранять.")
            context.user_data.pop('auto_save_pending', None)
    
    async def _ask_for_title_after_autosave(self, query, analysis: Dict):
        """Спрашивает название после автосохранения"""
        suggested_title = analysis.get('suggested_title', 'Без названия')
        category = analysis.get('category', 'other')
        description = analysis.get('description', '')
        
        category_emoji = self.content.CATEGORIES.get(category, "📂").split()[0]
        
        keyboard = [
            [InlineKeyboardButton("✅ Принять предложение", callback_data=f"content_accept_{suggested_title}")],
            [InlineKeyboardButton("✏️ Изменить название", callback_data="content_edit_title")],
            [InlineKeyboardButton("🔄 Другая категория", callback_data="content_change_category")],
            [InlineKeyboardButton("❌ Отменить", callback_data="content_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"✨ <b>Контент проанализирован!</b>\n\n"
            f"📝 <b>Описание:</b> {description}\n"
            f"{category_emoji} <b>Категория:</b> {category.title()}\n"
            f"💡 <b>Предложенное название:</b>\n<code>{suggested_title}</code>\n\n"
            f"Как сохраняем?"
        )
        
        await query.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

