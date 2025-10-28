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
                 extras_service=None, parser_service=None, agent_service=None):
        self.db = db
        self.ai = ai
        self.memory = memory
        self.agent = agent_service  # AI Агент для расширенной проактивности
        
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
        
        # Формируем системный промпт с памятью
        system_prompt = config.SYSTEM_PROMPT
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
        
        # === ВЫЗОВ ИИ С FUNCTION CALLING ===
        response = await self.ai.chat(
            messages=messages,
            functions=AVAILABLE_FUNCTIONS,  # Передаем доступные функции
            temperature=0.7,
            max_tokens=2000
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
                
                # Показываем результат пользователю
                await update.message.reply_text(function_result)
                
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
                
                # Получаем финальный ответ от ИИ (с учетом результата функции)
                final_response = await self.ai.chat(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                if final_response and isinstance(final_response, str):
                    # Если финальный ответ отличается от результата функции, отправляем его
                    if final_response != function_result and len(final_response) > 10:
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
                    max_tokens=1000
                )
                
                if final_response:
                    await self.db.add_message(user.id, "assistant", final_response)
                    # Если финальный ответ отличается от результата функции, отправляем его
                    if final_response != function_result and len(final_response) > 10:
                        await update.message.reply_text(final_response)
                
            else:
                # Обычный текстовый ответ
                await self.db.add_message(user.id, "assistant", response)
                await update.message.reply_text(response)
                
        except Exception as e:
            print(f"❌ Ошибка обработки ответа: {e}")
            # Fallback - отправляем как есть
            if isinstance(response, str):
                await self.db.add_message(user.id, "assistant", response)
                await update.message.reply_text(response)
            else:
                await update.message.reply_text(
                    "😔 Произошла ошибка при обработке ответа."
                )
        
        # === РАСШИРЕННАЯ ПРОАКТИВНОСТЬ АГЕНТА ===
        if self.agent and self.agent.is_enabled(user.id):
            try:
                # 1. Автоматическое извлечение задач из диалога
                tasks_result = await self.agent.extract_tasks_from_dialogue(user.id, message_text)
                
                if tasks_result and tasks_result.get("suggestion"):
                    await update.message.reply_text(
                        f"💡 {tasks_result['suggestion']}",
                        parse_mode='Markdown'
                    )
                
                # 2. Проверка завершения задач
                completion_msg = await self.agent.intelligent_task_completion(user.id, message_text)
                if completion_msg:
                    await update.message.reply_text(completion_msg)
                
                # 3. Предсказательные предложения (изредка)
                import random
                if random.random() < 0.1:  # 10% шанс
                    prediction = await self.agent.predictive_suggestions(user.id)
                    if prediction:
                        await update.message.reply_text(prediction)
                
            except Exception as e:
                print(f"⚠️ Ошибка расширенной проактивности: {e}")
    
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

