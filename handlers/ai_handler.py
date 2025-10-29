"""
Обработчики ИИ диалогов
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
import json

from database import Database
from services import AIService, MemoryService
from services.function_tools import AVAILABLE_FUNCTIONS, FunctionExecutor
import config


class AIHandler:
    def __init__(self, db: Database, ai: AIService, memory: MemoryService, 
                 extras_service=None, parser_service=None, agent_service=None, personality_service=None):
        self.db = db
        self.ai = ai
        self.memory = memory
        self.agent = agent_service  # AI Агент для расширенной проактивности
        self.personality = personality_service  # Живая личность для отслеживания активности
        
        # Function executor для выполнения функций
        self.function_executor = FunctionExecutor(
            db=db,
            memory_service=memory,
            extras_service=extras_service,
            parser_service=parser_service
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Основной обработчик текстовых сообщений с Function Calling
        """
        user = update.effective_user
        message_text = update.message.text
        
        # Обновляем активность пользователя для живой личности
        if self.personality:
            self.personality.update_user_activity(user.id)
        
        # Проверяем не является ли это кнопкой меню
        from handlers.menu_handler import MenuHandler
        menu_handler = MenuHandler()
        if await menu_handler.handle_menu_button(update, context):
            return
        
        # Показываем индикатор печати
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Сохраняем сообщение пользователя
        await self.db.add_message(user.id, "user", message_text)
        
        # Получаем контекст разговора
        recent_messages = await self.db.get_recent_messages(user.id)
        
        # Получаем долгосрочную память для контекста
        memory_context = await self.memory.get_context_for_ai(user.id)
        
        # Формируем системный промпт с памятью и текущей датой по Киеву
        from datetime import datetime, timedelta
        import pytz
        
        kiev_tz = pytz.timezone('Europe/Kiev')
        current_time = datetime.now(kiev_tz)
        current_date = current_time.strftime("%Y-%m-%d")
        current_datetime = current_time.strftime("%Y-%m-%d %H:%M")
        current_day = current_time.day
        current_month = current_time.month
        current_year = current_time.year
        yesterday = (current_time - timedelta(days=1)).strftime("%Y-%m-%d")
        day_before = (current_time - timedelta(days=2)).strftime("%Y-%m-%d")
        
        system_prompt = config.SYSTEM_PROMPT + f"""

📅 ТЕКУЩАЯ ДАТА И ВРЕМЯ (Киев/Украина):
Сейчас: {current_datetime} (день {current_day}, месяц {current_month}, год {current_year})
Сегодня: {current_date}
Вчера: {yesterday}
Позавчера: {day_before}

📊 ПРАВИЛА РАБОТЫ С ДАТАМИ:
1. Когда пользователь говорит "за 23" или "23 числа" - это означает {current_year}-{current_month:02d}-23
2. Когда говорит "за вчера" - используй дату {yesterday}
3. Когда "позавчера" - используй дату {day_before}
4. Когда называет только число (например "27") - это число текущего месяца {current_month}
5. Всегда формируй дату в формате YYYY-MM-DD
6. Если пользователь не указывает дату или говорит "сегодня", "сейчас" - НЕ передавай параметр date вообще

ПРИМЕРЫ:
- "статистика за 23" → date = "{current_year}-{current_month:02d}-23"
- "покажи за вчера" → date = "{yesterday}"
- "статистика за сегодня" → date НЕ передавать (оставить пустым)
- "за 27 число" → date = "{current_year}-{current_month:02d}-27"

📸 ВАЖНО! РАБОТА С ФОТО:
Когда пользователь просит ПОКАЗАТЬ/ОТПРАВИТЬ сохранённое фото, карту или изображение - ВСЕГДА используй функцию show_saved_content()! НЕ описывай фото текстом! НЕ отправляй ссылки! Отправляй РЕАЛЬНОЕ фото через функцию.
"""
        
        if memory_context:
            system_prompt += memory_context
        
        # Формируем сообщения для API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю
        for msg in recent_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Добавляем текущее сообщение если его еще нет
        if not recent_messages or recent_messages[-1]["content"] != message_text:
            messages.append({"role": "user", "content": message_text})
        
        # === Быстрые интенты без ИИ: показать сохранённые фото ===
        import re
        text_lower = message_text.lower()
        print(f"🔍 Проверяю интент: '{message_text}' -> '{text_lower}'")
        
        if re.search(r"(покажи|отправь|скинь).*(последн|свеж|крайн).*фото|последн.*фото", text_lower):
            print("✅ Найден интент 'показать последнее фото' - обрабатываю без ИИ")
            # Берём последнее сохранённое изображение из библиотеки
            items = await self.db.get_content(user.id, content_type='image', limit=1)
            print(f"📚 Найдено в БД: {len(items)} изображений")
            
            if items:
                item = items[0]
                print(f"📸 Данные фото: file_path={item.get('file_path')}, file_id={item.get('file_id')}")
                title = item.get('title', 'Без названия')
                category = item.get('category', 'other')
                caption = f"📸 <b>{title}</b>\n🏷 {category.title()}"
                try:
                    from pathlib import Path
                    if item.get('file_path') and Path(item['file_path']).exists():
                        print(f"📁 Отправляю из файла: {item['file_path']}")
                        with open(item['file_path'], 'rb') as photo:
                            await update.message.reply_photo(photo=photo, caption=caption, parse_mode='HTML')
                            print("✅ Фото отправлено успешно!")
                            return
                    elif item.get('file_id'):
                        print(f"📱 Отправляю по file_id: {item['file_id']}")
                        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=item['file_id'], caption=caption, parse_mode='HTML')
                        print("✅ Фото отправлено по file_id!")
                        return
                except Exception as e:
                    print(f"❌ Ошибка отправки фото: {e}")
                    pass
                await update.message.reply_text("⚠️ Не удалось отправить фото. Попробуй ещё раз или сохрани новое.")
                return
            else:
                print("❌ Нет сохранённых изображений в БД")
        else:
            print("❌ Интент 'показать фото' не найден, передаю в ИИ")

        # === ВЫЗОВ ИИ С FUNCTION CALLING ===
        response = await self.ai.chat(
            messages=messages,
            functions=AVAILABLE_FUNCTIONS,  # Передаем доступные функции
            temperature=0.7,
            max_tokens=800  # Оптимизация: 2000→800 (-60% токенов!)
        )
        
        if not response:
            await update.message.reply_text(
                "😔 Извини, произошла ошибка при обращении к ИИ. Попробуй еще раз."
            )
            return
        
        # === ПРОВЕРКА НА FUNCTION CALL ===
        # DeepSeek может вернуть либо текст, либо вызов функции
        # Проверяем есть ли вызов функции в ответе
        
        # Пытаемся обработать как обычный ответ
        try:
            # Новый формат: tool_calls (DeepSeek API v1)
            if isinstance(response, dict) and "tool_calls" in response and response["tool_calls"]:
                tool_call = response["tool_calls"][0]  # Берём первый вызов
                function_name = tool_call["function"]["name"]
                arguments = json.loads(tool_call["function"]["arguments"])
                
                # Выполняем функцию
                print(f"🔧 Вызов функции: {function_name} с аргументами: {arguments}")
                function_result = await self.function_executor.execute_function(
                    function_name=function_name,
                    arguments=arguments,
                    user_id=user.id
                )
                print(f"✅ Результат функции: {function_result[:200] if function_result else 'None'}...")
                
                # Проверяем, нужно ли отправить фото
                if function_result and function_result.startswith("SEND_PHOTOS:"):
                    print(f"📸 Обнаружен запрос на отправку фото: {function_result}")
                    # Формат: SEND_PHOTOS:worker_name|count
                    parts = function_result.replace("SEND_PHOTOS:", "").split("|")
                    worker_name = parts[0]
                    
                    from pathlib import Path
                    screenshots_dir = Path("data/screenshots")
                    screenshots = list(screenshots_dir.glob(f"*{worker_name}*.png"))
                    
                    print(f"📁 Найдено скриншотов: {len(screenshots)} в {screenshots_dir}")
                    
                    if screenshots:
                        await update.message.reply_text(f"📸 Отправляю скриншоты для {worker_name}...")
                        for screenshot_path in screenshots:
                            print(f"📤 Отправляю: {screenshot_path}")
                            try:
                                with open(screenshot_path, 'rb') as photo:
                                    await update.message.reply_photo(
                                        photo=photo,
                                        caption=f"Скриншот: {screenshot_path.name}"
                                    )
                            except Exception as e:
                                print(f"❌ Ошибка отправки фото: {e}")
                        function_result = f"✅ Отправлено скриншотов: {len(screenshots)}"
                    else:
                        print(f"⚠️ Скриншоты не найдены в {screenshots_dir}")
                
                # Обработка сохранённого контента из библиотеки
                elif function_result and function_result.startswith("SEND_CONTENT:"):
                    print(f"📚 Обнаружен запрос на отправку контента: {function_result}")
                    # Формат: SEND_CONTENT:id1,id2,id3
                    content_ids = function_result.replace("SEND_CONTENT:", "").split(",")
                    
                    sent_count = 0
                    for content_id in content_ids:
                        try:
                            # Получаем данные контента из БД
                            content = await self.db.get_content(update.effective_user.id, content_id=int(content_id.strip()))
                            
                            if not content:
                                continue
                            
                            item = content[0]  # get_content возвращает список
                            content_type = item.get('content_type', 'unknown')
                            title = item.get('title', 'Без названия')
                            category = item.get('category', 'other')
                            
                            caption = f"📸 <b>{title}</b>\n🏷 {category.title()}"
                            
                            # Отправляем в зависимости от типа
                            if content_type == "image":
                                # Приоритет: file_path > file_id
                                if item.get('file_path'):
                                    from pathlib import Path
                                    file_path = Path(item['file_path'])
                                    if file_path.exists():
                                        with open(file_path, 'rb') as photo:
                                            await update.message.reply_photo(
                                                photo=photo,
                                                caption=caption,
                                                parse_mode='HTML'
                                            )
                                        sent_count += 1
                                elif item.get('file_id'):
                                    try:
                                        await context.bot.send_photo(
                                            chat_id=update.effective_chat.id,
                                            photo=item['file_id'],
                                            caption=caption,
                                            parse_mode='HTML'
                                        )
                                        sent_count += 1
                                    except:
                                        pass  # file_id истёк
                        
                        except Exception as e:
                            print(f"❌ Ошибка отправки контента {content_id}: {e}")
                    
                    if sent_count > 0:
                        function_result = f"✅ Отправлено фото: {sent_count}"
                    else:
                        function_result = "❌ Не удалось отправить фото"
                
                # Показываем результат пользователю (определяем формат)
                # Проверяем на HTML теги
                if '<b>' in function_result or '<i>' in function_result or '<code>' in function_result:
                    parse_mode = 'HTML'
                # Проверяем на Markdown
                elif '**' in function_result or '__' in function_result or '`' in function_result:
                    parse_mode = 'Markdown'
                else:
                    parse_mode = None
                
                await update.message.reply_text(function_result, parse_mode=parse_mode)
                
                # Добавляем в БД как сообщение ассистента
                await self.db.add_message(user.id, "assistant", function_result)
                
                # ВАЖНО: Сначала добавляем сообщение ассистента с tool_calls
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": response["tool_calls"]
                })
                
                # Затем добавляем ответ от функции
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": function_result
                })
                
                # Финальный ответ ТОЛЬКО для статистики, НЕ для скриншотов
                if function_name == 'get_work_stats':
                    # Добавляем инструкцию для AI
                    messages.append({
                        "role": "system",
                        "content": """ВАЖНО: Пользователь уже получил отчет выше. 
                        
Дай ОЧЕНЬ КРАТКОЕ резюме (максимум 2 предложения):
- Кто лидер и кто отстает
- Главная проблема (если есть)

НЕ ПЕРЕЧИСЛЯЙ всех! НЕ ДУБЛИРУЙ цифры! Только самое важное.
Пиши как человек, без "рекомендую", "предлагаю" и т.д."""
                    })
                    
                    final_response = await self.ai.chat(
                        messages=messages,
                        temperature=0.7,
                        max_tokens=120  # Оптимизация: 150→120 для краткости
                    )
                    
                    if final_response and isinstance(final_response, str) and len(final_response) > 10:
                        await update.message.reply_text(final_response)
                        await self.db.add_message(user.id, "assistant", final_response)
            
            # Старый формат: function_call (для обратной совместимости)
            elif isinstance(response, dict) and "function_call" in response:
                function_name = response["function_call"]["name"]
                arguments = json.loads(response["function_call"]["arguments"])
                
                # Выполняем функцию
                function_result = await self.function_executor.execute_function(
                    function_name=function_name,
                    arguments=arguments,
                    user_id=user.id
                )
                
                # Показываем результат
                await update.message.reply_text(function_result)
                
                # Добавляем результат функции в контекст для финального ответа
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": function_result
                })
                
                # Получаем финальный ответ от ИИ (с учетом результата функции)
                final_response = await self.ai.chat(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=200  # Оптимизация: 1000→200 (-80% токенов!)
                )
                
                if final_response:
                    await self.db.add_message(user.id, "assistant", final_response)
                    # Если финальный ответ отличается от результата функции, отправляем его
                    if final_response != function_result and len(final_response) > 10:
                        # Определяем формат
                        if '<b>' in final_response or '<i>' in final_response or '<code>' in final_response:
                            parse_mode = 'HTML'
                        elif '**' in final_response or '__' in final_response or '`' in final_response:
                            parse_mode = 'Markdown'
                        else:
                            parse_mode = None
                        await update.message.reply_text(final_response, parse_mode=parse_mode)
                
            else:
                # Fallback: если пользователь просил последнее фото, отправляем фото вместо текста
                import re as _re
                text_lower = message_text.lower()
                print(f"🔄 Fallback проверка: '{message_text}' -> '{text_lower}'")
                
                if _re.search(r"(покажи|отправь|скинь).*(последн|свеж|крайн).*фото|последн.*фото", text_lower):
                    print("✅ Fallback: Найден интент 'показать последнее фото'")
                    items = await self.db.get_content(user.id, content_type='image', limit=1)
                    print(f"📚 Fallback: Найдено в БД: {len(items)} изображений")
                    
                    if items:
                        item = items[0]
                        print(f"📸 Fallback: Данные фото: file_path={item.get('file_path')}, file_id={item.get('file_id')}")
                        title = item.get('title', 'Без названия')
                        category = item.get('category', 'other')
                        caption = f"📸 <b>{title}</b>\n🏷 {category.title()}"
                        try:
                            from pathlib import Path
                            if item.get('file_path') and Path(item['file_path']).exists():
                                print(f"📁 Fallback: Отправляю из файла: {item['file_path']}")
                                with open(item['file_path'], 'rb') as photo:
                                    await update.message.reply_photo(photo=photo, caption=caption, parse_mode='HTML')
                                    print("✅ Fallback: Фото отправлено успешно!")
                                    return
                            elif item.get('file_id'):
                                print(f"📱 Fallback: Отправляю по file_id: {item['file_id']}")
                                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=item['file_id'], caption=caption, parse_mode='HTML')
                                print("✅ Fallback: Фото отправлено по file_id!")
                                return
                        except Exception as e:
                            print(f"❌ Fallback: Ошибка отправки фото: {e}")
                            pass
                    else:
                        print("❌ Fallback: Нет сохранённых изображений в БД")
                else:
                    print("❌ Fallback: Интент 'показать фото' не найден")
                
                # Обычный текстовый ответ - определяем формат
                if '<b>' in response or '<i>' in response or '<code>' in response:
                    parse_mode = 'HTML'
                elif '**' in response or '__' in response or '`' in response:
                    parse_mode = 'Markdown'
                else:
                    parse_mode = None
                
                # Валидация HTML перед отправкой
                if parse_mode == 'HTML':
                    try:
                        # Простая проверка - если есть незакрытые теги, убираем HTML
                        if response.count('<b>') != response.count('</b>') or \
                           response.count('<i>') != response.count('</i>') or \
                           response.count('<code>') != response.count('</code>'):
                            print("⚠️ Неправильный HTML, отправляю как текст")
                            parse_mode = None
                    except:
                        parse_mode = None
                
                await self.db.add_message(user.id, "assistant", response)
                await update.message.reply_text(response, parse_mode=parse_mode)
                
        except Exception as e:
            print(f"❌ Ошибка обработки ответа: {e}")
            # Fallback - отправляем как есть с определением формата
            if isinstance(response, str):
                # Определяем формат даже в fallback
                if '<b>' in response or '<i>' in response or '<code>' in response:
                    parse_mode = 'HTML'
                elif '**' in response or '__' in response or '`' in response:
                    parse_mode = 'Markdown'
                else:
                    parse_mode = None
                
                await self.db.add_message(user.id, "assistant", response)
                await update.message.reply_text(response, parse_mode=parse_mode)
            else:
                await update.message.reply_text(
                    "😔 Произошла ошибка при обработке ответа."
                )
        
        # === РАСШИРЕННАЯ ПРОАКТИВНОСТЬ АГЕНТА (ОТКЛЮЧЕНА) ===
        # Закомментировано - пользователь посчитал это назойливым
        pass
        # if self.agent and self.agent.is_enabled(user.id):
        #     try:
        #         # 1. Автоматическое извлечение задач из диалога
        #         tasks_result = await self.agent.extract_tasks_from_dialogue(user.id, message_text)
        #         
        #         if tasks_result and tasks_result.get("suggestion"):
        #             await update.message.reply_text(
        #                 f"💡 {tasks_result['suggestion']}",
        #                 parse_mode='Markdown'
        #             )
        #         
        #         # 2. Проверка завершения задач
        #         completion_msg = await self.agent.intelligent_task_completion(user.id, message_text)
        #         if completion_msg:
        #             await update.message.reply_text(completion_msg)
        #         
        #         # 3. Предсказательные предложения (изредка)
        #         import random
        #         if random.random() < 0.1:  # 10% шанс
        #             prediction = await self.agent.predictive_suggestions(user.id)
        #             if prediction:
        #                 await update.message.reply_text(prediction)
        #         
        #     except Exception as e:
        #         print(f"⚠️ Ошибка расширенной проактивности: {e}")
    
    async def clear_context_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /clear - очищает историю диалога
        """
        user = update.effective_user
        
        await self.db.clear_conversation(user.id)
        await update.message.reply_text(
            "🧹 История диалога очищена. Начинаем с чистого листа!"
        )
    
    async def summarize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /summarize - резюмирует последнюю часть разговора
        """
        user = update.effective_user
        
        # Получаем последние сообщения
        messages = await self.db.get_recent_messages(user.id, limit=10)
        
        if not messages:
            await update.message.reply_text("📭 Нет сообщений для резюмирования.")
            return
        
        # Формируем текст для резюмирования
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        summary = await self.ai.summarize_text(conversation_text)
        
        if summary:
            await update.message.reply_text(f"📝 **Краткая выжимка разговора:**\n\n{summary}")
        else:
            await update.message.reply_text("😔 Не удалось создать резюме.")
    
    async def think_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /think <вопрос> - использует reasoning mode (deepseek-reasoner)
        Показывает процесс рассуждения модели для сложных задач
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "🤔 **Режим глубоких рассуждений**\n\n"
                "Используй эту команду для сложных вопросов, требующих анализа.\n"
                "Модель покажет процесс мышления и придет к выводу.\n\n"
                "Использование:\n"
                "`/think <ваш вопрос>`\n\n"
                "Примеры:\n"
                "• `/think Как лучше организовать код для масштабируемости?`\n"
                "• `/think Проанализируй плюсы и минусы Python vs Go`\n"
                "• `/think Какую стратегию выбрать для увеличения продаж?`",
                parse_mode='Markdown'
            )
            return
        
        question = " ".join(context.args)
        
        await update.message.reply_text("🤔 Думаю... (это может занять ~10-20 секунд)")
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Получаем последние сообщения для контекста
        recent_messages = await self.db.get_recent_messages(user.id, limit=3)
        
        # Получаем память для контекста
        memory_context = await self.memory.get_context_for_ai(user.id)
        system_prompt = None
        if memory_context:
            system_prompt = f"Ты помощник, который глубоко анализирует вопросы.{memory_context}"
        
        # Используем reasoning mode
        response = await self.ai.reasoning_chat(
            user_message=question,
            context_messages=recent_messages,
            system_prompt=system_prompt
        )
        
        if response:
            # Сохраняем в историю
            await self.db.add_message(user.id, "user", f"[THINK] {question}")
            await self.db.add_message(user.id, "assistant", response)
            
            # Отправляем ответ (может быть длинным)
            # Разбиваем на части если нужно
            if len(response) > 4000:
                parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for part in parts:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "😔 Не удалось получить ответ. Попробуй еще раз."
            )

