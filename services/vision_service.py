"""
Сервис для работы с изображениями через Google Gemini
"""
import google.generativeai as genai
from PIL import Image
import io
import os
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import config
import logging

logger = logging.getLogger(__name__)


class VisionService:
    """
    Анализ изображений через Google Gemini Flash
    Использует стабильный SDK от Google
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.executor = ThreadPoolExecutor(max_workers=2)  # Для асинхронных вызовов
        
        if self.api_key:
            # Настраиваем API
            genai.configure(api_key=self.api_key)
            self.model_name = "gemini-1.5-flash"  # Стабильная модель с поддержкой изображений
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"✅ Gemini Vision Service инициализирован ({self.model_name})")
        else:
            logger.warning("⚠️ GEMINI_API_KEY не найден в .env")
            self.model = None
            self.model_name = None
    
    async def analyze_image(self, 
                           image_bytes: bytes, 
                           question: str = None,
                           language: str = "ru") -> Optional[str]:
        """
        Анализирует изображение
        
        Args:
            image_bytes: Байты изображения
            question: Вопрос по изображению (опционально)
            language: Язык ответа (ru/uk/en)
            
        Returns:
            Ответ от модели
        """
        if not self.model:
            return "❌ Gemini API не настроен. Добавь GEMINI_API_KEY в .env"
        
        try:
            # Формируем промпт
            if question:
                prompt = question
            else:
                if language == "ru":
                    prompt = "Опиши подробно что изображено на этой картинке"
                elif language == "uk":
                    prompt = "Опиши детально що зображено на цій картинці"
                else:
                    prompt = "Describe in detail what is shown in this image"
            
            # Открываем изображение через PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            # Запускаем синхронный вызов Gemini в отдельном потоке
            # чтобы не блокировать event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.model.generate_content([prompt, image])
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа изображения: {e}")
            return f"❌ Ошибка при анализе изображения: {str(e)}"
    
    async def ocr_image(self, image_bytes: bytes) -> Optional[str]:
        """
        Распознает текст на изображении (OCR)
        
        Args:
            image_bytes: Байты изображения
            
        Returns:
            Распознанный текст
        """
        if not self.model:
            return "❌ Gemini API не настроен"
        
        try:
            prompt = """Распознай весь текст на этом изображении.
Верни только текст, без дополнительных комментариев.
Сохрани форматирование и структуру.
Если текста нет - напиши "Текст не обнаружен"."""
            
            # Открываем изображение через PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            # Асинхронный вызов через executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.model.generate_content([prompt, image])
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Ошибка OCR: {e}")
            return f"❌ Ошибка при распознавании текста: {str(e)}"
    
    async def analyze_code(self, image_bytes: bytes) -> Optional[str]:
        """
        Анализирует код на скриншоте
        
        Args:
            image_bytes: Байты изображения
            
        Returns:
            Анализ кода
        """
        if not self.model:
            return "❌ Gemini API не настроен"
        
        try:
            prompt = """Проанализируй код на этом скриншоте:

1. Что делает этот код?
2. Есть ли ошибки или опечатки?
3. Можно ли улучшить?
4. Какие best practices не соблюдены?

Отвечай на русском языке четко и структурировано."""
            
            # Открываем изображение через PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            # Асинхронный вызов через executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.model.generate_content([prompt, image])
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа кода: {e}")
            return f"❌ Ошибка: {str(e)}"
    
    async def analyze_chart(self, image_bytes: bytes) -> Optional[str]:
        """
        Анализирует график или диаграмму
        
        Args:
            image_bytes: Байты изображения
            
        Returns:
            Анализ графика
        """
        if not self.model:
            return "❌ Gemini API не настроен"
        
        try:
            prompt = """Проанализируй график/диаграмму на изображении:

1. Какой тип графика?
2. Что показывает?
3. Какой тренд наблюдается?
4. Есть ли аномалии или интересные точки?
5. Выводы и рекомендации

Отвечай на русском языке."""
            
            # Открываем изображение через PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            # Асинхронный вызов через executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.model.generate_content([prompt, image])
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа графика: {e}")
            return f"❌ Ошибка: {str(e)}"

