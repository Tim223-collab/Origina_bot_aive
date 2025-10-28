"""
Обработчики изображений
"""
import random
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from services.vision_service import VisionService
from services.ai_service import AIService


class ImageHandler:
    """Обработка изображений через Gemini Vision + DeepSeek улучшение"""
    
    # Живые сообщения от AIVE для разнообразия
    GREETING_MESSAGES = [
        "👋 AIVE на связи! Сейчас посмотрю...",
        "🤖 Привет! Уже смотрю что тут...",
        "👀 О, интересно! Смотрю...",
        "💫 AIVE к вашим услугам! Изучаю фото...",
        "✨ Дай взгляну на это..."
    ]
    
    THINKING_MESSAGES = {
        "describe": [
            "🤔 Думаю над ответом...",
            "💭 Формулирую описание...",
            "✍️ Готовлю детальный ответ...",
            "🎨 Оформляю информацию..."
        ],
        "ocr": [
            "✍️ Сейчас всё красиво оформлю...",
            "📝 Структурирую текст...",
            "✨ Делаю читабельным...",
            "🎯 Форматирую результат..."
        ],
        "code": [
            "💡 Готовлю детальный анализ и рекомендации...",
            "🔍 Ищу способы улучшить код...",
            "📊 Оцениваю качество...",
            "✅ Составляю рекомендации..."
        ],
        "chart": [
            "🔍 Ищу тренды и делаю выводы...",
            "📈 Анализирую данные...",
            "💡 Готовлю инсайты...",
            "📊 Формулирую рекомендации..."
        ]
    }
    
    def __init__(self, vision_service: VisionService, ai_service: AIService):
        self.vision = vision_service
        self.ai = ai_service
    
    async def _enhance_with_deepseek(self, gemini_result: str, analysis_type: str, user_question: str = None) -> str:
        """
        Улучшает результат от Gemini через DeepSeek
        
        Args:
            gemini_result: Результат анализа от Gemini
            analysis_type: Тип анализа (describe/ocr/code/chart)
            user_question: Вопрос пользователя (если есть)
        
        Returns:
            Улучшенный и структурированный ответ
        """
        prompts = {
            "describe": """Ты получил описание изображения от другой AI модели. 
Твоя задача - улучшить этот результат:
1. Сделать текст более структурированным и читабельным
2. Добавить интересные детали и контекст
3. Если пользователь задал вопрос - ответить на него четко
4. Добавить эмодзи для лучшего восприятия

Исходное описание от AI:
{result}

{question_part}

Улучшенное описание:""",

            "ocr": """Ты получил распознанный текст с изображения от OCR модели.
Твоя задача:
1. Проверить и улучшить форматирование
2. Исправить явные ошибки распознавания (если есть)
3. Добавить структуру (заголовки, списки если нужно)
4. Сделать текст более читабельным

Распознанный текст:
{result}

Улучшенный текст:""",

            "code": """Ты получил анализ кода от другой AI. 
Твоя задача - сделать анализ более полезным:
1. Структурировать по категориям (функционал, ошибки, улучшения)
2. Добавить конкретные рекомендации
3. Показать примеры исправлений (если нужно)
4. Оценить качество кода (1-10)
5. Добавить эмодзи для наглядности

Исходный анализ:
{result}

Улучшенный анализ:""",

            "chart": """Ты получил анализ графика/диаграммы от другой AI.
Твоя задача - сделать анализ более профессиональным:
1. Структурировать информацию четко
2. Добавить численные оценки трендов
3. Дать практические рекомендации на основе данных
4. Выделить ключевые инсайты
5. Добавить визуальные разделители

Исходный анализ:
{result}

Профессиональный анализ:"""
        }
        
        # Формируем промпт
        prompt_template = prompts.get(analysis_type, prompts["describe"])
        question_part = f"\nВопрос пользователя: {user_question}" if user_question else ""
        prompt = prompt_template.format(result=gemini_result, question_part=question_part)
        
        # Отправляем в DeepSeek для улучшения
        messages = [
            {
                "role": "system",
                "content": "Ты эксперт по улучшению и структурированию информации. Делай ответы понятными, полезными и красиво оформленными."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        enhanced_result = await self.ai.chat(messages, temperature=0.7, max_tokens=2000)
        
        return enhanced_result if enhanced_result else gemini_result
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обрабатывает фото от пользователя
        """
        user = update.effective_user
        
        # Получаем самое большое фото
        photo = update.message.photo[-1]
        
        # Получаем подпись (если есть)
        caption = update.message.caption or ""
        
        await update.message.reply_text(random.choice(self.GREETING_MESSAGES))
        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            # Скачиваем фото
            file = await context.bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()
            
            # Определяем что нужно сделать на основе подписи
            caption_lower = caption.lower()
            
            if any(word in caption_lower for word in ['текст', 'ocr', 'распознай', 'прочитай', 'text']):
                # OCR - распознавание текста
                await update.message.reply_text("👀 Вглядываюсь в текст...")
                gemini_result = await self.vision.ocr_image(bytes(image_bytes))
                
                await update.message.reply_text(random.choice(self.THINKING_MESSAGES["ocr"]))
                result = await self._enhance_with_deepseek(gemini_result, "ocr")
                response = f"📄 **Распознанный текст:**\n\n{result}"
            
            elif any(word in caption_lower for word in ['код', 'code', 'ошибка', 'bug', 'баг']):
                # Анализ кода
                await update.message.reply_text("👨‍💻 Читаю код...")
                gemini_result = await self.vision.analyze_code(bytes(image_bytes))
                
                await update.message.reply_text(random.choice(self.THINKING_MESSAGES["code"]))
                result = await self._enhance_with_deepseek(gemini_result, "code")
                response = f"💻 **Анализ кода:**\n\n{result}"
            
            elif any(word in caption_lower for word in ['график', 'диаграмм', 'chart', 'graph', 'статистик']):
                # Анализ графика
                await update.message.reply_text("📊 Изучаю график...")
                gemini_result = await self.vision.analyze_chart(bytes(image_bytes))
                
                await update.message.reply_text(random.choice(self.THINKING_MESSAGES["chart"]))
                result = await self._enhance_with_deepseek(gemini_result, "chart")
                response = f"📊 **Анализ графика:**\n\n{result}"
            
            else:
                # Обычный анализ с вопросом или описание
                await update.message.reply_text("👁️ Смотрю на изображение...")
                gemini_result = await self.vision.analyze_image(
                    bytes(image_bytes),
                    question=caption if caption else None
                )
                
                await update.message.reply_text(random.choice(self.THINKING_MESSAGES["describe"]))
                result = await self._enhance_with_deepseek(
                    gemini_result, 
                    "describe",
                    user_question=caption if caption else None
                )
                response = f"📸 **Анализ изображения:**\n\n{result}"
            
            # Отправляем ответ
            # Разбиваем на части если длинный
            if len(response) > 4000:
                parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for part in parts:
                    await update.message.reply_text(part, parse_mode='Markdown')
            else:
                await update.message.reply_text(response, parse_mode='Markdown')
            
            print(f"✅ Обработано изображение от {user.first_name}")
            
        except Exception as e:
            print(f"❌ Ошибка обработки фото: {e}")
            await update.message.reply_text(
                f"😔 Ошибка при обработке изображения.\n\n"
                f"Проверь что GEMINI_API_KEY настроен в .env файле."
            )
    
    async def ocr_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /ocr - справка по распознаванию текста
        """
        await update.message.reply_text(
            "📄 **OCR (распознавание текста)**\n\n"
            "Отправь фото с текстом и добавь подпись:\n"
            "• `текст` или `ocr`\n"
            "• `прочитай` или `распознай`\n\n"
            "**Примеры:**\n"
            "• Фото документа + подпись 'текст'\n"
            "• Фото чека + подпись 'прочитай'\n"
            "• Скриншот переписки + подпись 'ocr'\n\n"
            "Поддерживаются: русский, украинский, английский и другие языки!",
            parse_mode='Markdown'
        )
    
    async def describe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /describe - справка по описанию изображений
        """
        await update.message.reply_text(
            "📸 **Описание изображений**\n\n"
            "Просто отправь фото - я опишу что на нем!\n\n"
            "**Или добавь подпись с вопросом:**\n"
            "• 'Что это?' - общее описание\n"
            "• 'Какой цвет?' - про цвета\n"
            "• 'Где это?' - про место\n"
            "• Любой другой вопрос\n\n"
            "**Специальные режимы:**\n"
            "• Подпись 'код' - анализ кода\n"
            "• Подпись 'текст' - OCR\n"
            "• Подпись 'график' - анализ графиков\n\n"
            "**Примеры:**\n"
            "• Фото еды - опишу блюдо\n"
            "• Фото природы - расскажу о месте\n"
            "• Скриншот кода + 'код' - найду ошибки\n"
            "• Фото графика + 'график' - проанализирую тренд",
            parse_mode='Markdown'
        )
    
    async def photo_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /photo - полная справка по работе с изображениями
        """
        await update.message.reply_text(
            "📸 **Работа с изображениями**\n\n"
            "**🎯 Основные возможности:**\n\n"
            "1️⃣ **Описание изображений**\n"
            "   • Просто отправь фото\n"
            "   • Или добавь вопрос в подписи\n\n"
            "2️⃣ **OCR (распознавание текста)**\n"
            "   • Фото + подпись 'текст'\n"
            "   • Работает с документами, чеками, надписями\n\n"
            "3️⃣ **Анализ кода**\n"
            "   • Скриншот кода + подпись 'код'\n"
            "   • Найду ошибки и дам рекомендации\n\n"
            "4️⃣ **Анализ графиков**\n"
            "   • График + подпись 'график'\n"
            "   • Проанализирую тренды и дам выводы\n\n"
            "**⚙️ Команды:**\n"
            "• /describe - как описывать фото\n"
            "• /ocr - как распознавать текст\n"
            "• /photo - эта справка\n\n"
            "**💡 Совет:**\n"
            "Задавай конкретные вопросы в подписи для лучших результатов!\n\n"
            "**📊 Лимиты:**\n"
            "Бесплатно: 1500 изображений/день",
            parse_mode='Markdown'
        )

