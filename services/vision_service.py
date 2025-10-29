"""
Сервис для работы с изображениями через Google Gemini
"""
from google import genai
from PIL import Image
import io
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import config
import logging

logger = logging.getLogger(__name__)


class VisionService:
    """
    Анализ изображений через Google Gemini
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        if self.api_key:
            # Используем НОВЫЙ SDK google-genai (уже установлен!)
            self.client = genai.Client(api_key=self.api_key)
            # Попробуем разные варианты модели
            self.model_name = "gemini-2.0-flash-exp"  # Экспериментальная модель
            logger.info(f"✅ Gemini Vision Service инициализирован ({self.model_name})")
        else:
            logger.warning("⚠️ GEMINI_API_KEY не найден в .env")
            self.client = None
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
        if not self.client:
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
            
            # Конвертируем в base64 для нового API
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Новый API - используем client.models.generate_content
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents={
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                )
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
        if not self.client:
            return "❌ Gemini API не настроен"
        
        try:
            prompt = """Распознай весь текст на этом изображении.
Верни только текст, без дополнительных комментариев.
Сохрани форматирование и структуру.
Если текста нет - напиши "Текст не обнаружен"."""
            
            # Конвертируем в base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Асинхронный вызов через executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents={
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
                        ]
                    }
                )
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
        if not self.client:
            return "❌ Gemini API не настроен"
        
        try:
            prompt = """Проанализируй код на этом скриншоте:

1. Что делает этот код?
2. Есть ли ошибки или опечатки?
3. Можно ли улучшить?
4. Какие best practices не соблюдены?

Отвечай на русском языке четко и структурировано."""
            
            # Конвертируем в base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Асинхронный вызов через executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents={
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
                        ]
                    }
                )
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
        if not self.client:
            return "❌ Gemini API не настроен"
        
        try:
            prompt = """Проанализируй график/диаграмму на изображении:

1. Какой тип графика?
2. Что показывает?
3. Какой тренд наблюдается?
4. Есть ли аномалии или интересные точки?
5. Выводы и рекомендации

Отвечай на русском языке."""
            
            # Конвертируем в base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Асинхронный вызов через executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents={
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
                        ]
                    }
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа графика: {e}")
            return f"❌ Ошибка: {str(e)}"

