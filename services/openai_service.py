"""
Сервис для работы с OpenAI ChatGPT API
"""
import openai
import os
from typing import List, Dict, Optional
import config


class OpenAIService:
    """
    OpenAI ChatGPT API клиент
    
    Модели:
    - gpt-4o: Лучшее качество, быстрый ($5/$15 per 1M)
    - gpt-4o-mini: Хороший баланс ($0.15/$0.60 per 1M)
    - gpt-4-turbo: Предыдущая версия
    """
    
    def __init__(self, api_key: str = None, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model_name = model_name
        
        if self.api_key:
            openai.api_key = self.api_key
        else:
            print("⚠️ OPENAI_API_KEY не найден - ChatGPT недоступен")
    
    def is_available(self) -> bool:
        """Проверяет доступность OpenAI API"""
        return self.api_key is not None
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> Optional[str]:
        """
        Отправляет запрос к ChatGPT API
        
        Args:
            messages: Список сообщений [{"role": "user/assistant/system", "content": "..."}]
            temperature: Температура генерации (0.0-2.0)
            max_tokens: Максимум токенов в ответе
            stream: Потоковая отправка (не реализовано)
        
        Returns:
            Ответ от модели или None в случае ошибки
        """
        if not self.is_available():
            return None
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ OpenAI API Error: {e}")
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
        
        # Системный промпт
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": config.SYSTEM_PROMPT})
        
        # Добавляем контекст (ограничиваем количество)
        for msg in context_messages[-config.MAX_CONTEXT_MESSAGES:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Добавляем новое сообщение
        messages.append({"role": "user", "content": user_message})
        
        return await self.chat(messages, temperature=0.7)
    
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
        
        messages = [
            {"role": "system", "content": "Ты эксперт по извлечению структурированных данных. Отвечаешь только валидным JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat(messages, temperature=0.1, max_tokens=1000)
        
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
                return None
        return None
    
    async def analyze_with_vision(
        self,
        text: str,
        image_url: str
    ) -> Optional[str]:
        """
        Анализ изображения (GPT-4o Vision)
        
        Args:
            text: Текстовый промпт
            image_url: URL изображения или base64
        
        Returns:
            Ответ с анализом
        """
        if not self.is_available():
            return None
        
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",  # Vision требует gpt-4o
                messages=messages,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ OpenAI Vision Error: {e}")
            return None
    
    async def summarize_text(self, text: str) -> Optional[str]:
        """Создает краткое резюме текста"""
        messages = [
            {"role": "system", "content": "Ты помощник который делает краткие выжимки текста на русском языке."},
            {"role": "user", "content": f"Сделай краткую выжимку этого текста:\n\n{text}"}
        ]
        return await self.chat(messages, temperature=0.3, max_tokens=500)
    
    async def extract_facts(self, text: str) -> Optional[str]:
        """Извлекает важные факты из текста для долгосрочной памяти"""
        messages = [
            {
                "role": "system", 
                "content": "Извлеки из текста важные факты, предпочтения, даты и информацию, которую стоит запомнить. Отвечай списком фактов."
            },
            {"role": "user", "content": text}
        ]
        return await self.chat(messages, temperature=0.2, max_tokens=500)

