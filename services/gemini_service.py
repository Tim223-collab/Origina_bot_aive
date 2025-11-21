"""
Сервис для работы с Google Gemini 2.0 Flash API
Документация: https://ai.google.dev/
"""
import google.generativeai as genai
import os
from typing import List, Dict, Optional
import config


class GeminiService:
    """
    Google Gemini 2.0 Flash API клиент
    
    Особенности:
    - Бесплатно до 1500 запросов/день
    - 1M токенов контекста
    - Мультимодальность (текст, изображения, видео)
    - Быстрый
    """
    
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        
        # Настройка API
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None
            print("⚠️ GEMINI_API_KEY не найден - Gemini недоступен")
    
    def is_available(self) -> bool:
        """Проверяет доступность Gemini API"""
        return self.model is not None
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Отправляет запрос к Gemini API
        
        Args:
            messages: Список сообщений [{"role": "user/model", "parts": ["content"]}]
            temperature: Температура генерации (0.0-2.0)
            max_tokens: Максимум токенов в ответе
        
        Returns:
            Ответ от модели или None в случае ошибки
        """
        if not self.is_available():
            return None
        
        try:
            # Конвертируем формат messages из OpenAI-style в Gemini-style
            gemini_messages = self._convert_messages(messages)
            
            # Конфигурация генерации
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Отправляем запрос
            response = self.model.generate_content(
                gemini_messages,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            return None
    
    async def chat_with_context(
        self,
        user_message: str,
        context_messages: List[Dict[str, str]],
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Чат с учетом контекста предыдущих сообщений
        
        Args:
            user_message: Новое сообщение пользователя
            context_messages: История предыдущих сообщений
            system_prompt: Системный промпт (опционально)
        
        Returns:
            Ответ ИИ
        """
        messages = []
        
        # В Gemini системный промпт идет как первое сообщение модели
        if system_prompt:
            messages.append({
                "role": "model",
                "parts": [system_prompt]
            })
        
        # Добавляем контекст (ограничиваем количество)
        for msg in context_messages[-config.MAX_CONTEXT_MESSAGES:]:
            messages.append(self._convert_single_message(msg))
        
        # Добавляем новое сообщение
        messages.append({
            "role": "user",
            "parts": [user_message]
        })
        
        return await self.chat(messages, temperature=0.7)
    
    async def analyze_with_image(
        self,
        text: str,
        image_data: bytes,
        mime_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Анализ изображения с текстовым промптом
        
        Args:
            text: Текстовый промпт
            image_data: Байты изображения
            mime_type: MIME тип изображения
        
        Returns:
            Ответ с анализом
        """
        if not self.is_available():
            return None
        
        try:
            # Создаем multimodal content
            image_part = {
                "mime_type": mime_type,
                "data": image_data
            }
            
            response = self.model.generate_content([text, image_part])
            return response.text
            
        except Exception as e:
            print(f"❌ Gemini Vision Error: {e}")
            return None
    
    async def extract_json(
        self,
        text: str,
        schema_description: str
    ) -> Optional[Dict]:
        """
        Извлекает структурированные данные в JSON формате
        
        Args:
            text: Текст для анализа
            schema_description: Описание нужной структуры данных
        
        Returns:
            Словарь с извлеченными данными
        """
        prompt = f"""Извлеки из текста данные и верни ТОЛЬКО валидный JSON без дополнительного текста.

Структура: {schema_description}

Текст: {text}

JSON:"""
        
        response = await self.chat([{
            "role": "user",
            "parts": [prompt]
        }], temperature=0.1)
        
        if response:
            try:
                import json
                # Убираем markdown code blocks если есть
                clean_response = response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.startswith("```"):
                    clean_response = clean_response[3:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                return json.loads(clean_response)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(f"Response was: {response}")
                return None
        return None
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict]:
        """Конвертирует OpenAI-style messages в Gemini-style"""
        gemini_messages = []
        
        for msg in messages:
            gemini_messages.append(self._convert_single_message(msg))
        
        return gemini_messages
    
    def _convert_single_message(self, msg: Dict[str, str]) -> Dict:
        """Конвертирует одно сообщение"""
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Gemini использует "user" и "model" вместо "user" и "assistant"
        if role == "assistant":
            role = "model"
        elif role == "system":
            # Системные сообщения преобразуем в сообщения модели
            role = "model"
        
        return {
            "role": role,
            "parts": [content]
        }
    
    async def summarize_text(self, text: str) -> Optional[str]:
        """Создает краткое резюме текста"""
        messages = [{
            "role": "user",
            "parts": [f"Сделай краткую выжимку этого текста на русском языке:\n\n{text}"]
        }]
        return await self.chat(messages, temperature=0.3, max_tokens=500)
    
    async def extract_facts(self, text: str) -> Optional[str]:
        """Извлекает важные факты из текста для долгосрочной памяти"""
        messages = [{
            "role": "user",
            "parts": [f"Извлеки из текста важные факты, предпочтения, даты и информацию, которую стоит запомнить. Отвечай списком фактов.\n\nТекст: {text}"]
        }]
        return await self.chat(messages, temperature=0.2, max_tokens=500)

