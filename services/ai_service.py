"""
Сервис для работы с DeepSeek API
Документация: https://api-docs.deepseek.com/
"""
import aiohttp
import asyncio
import json
from typing import List, Dict, Optional, AsyncIterator, Any
import config


class AIService:
    """
    DeepSeek API клиент с поддержкой всех возможностей:
    - deepseek-chat (non-thinking mode)
    - deepseek-reasoner (thinking mode)
    - Streaming
    - Function calling
    - JSON output
    - Context caching
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.model = model or config.DEEPSEEK_MODEL
        self.api_url = config.DEEPSEEK_API_URL
        self.reasoning_model = "deepseek-reasoner"  # Thinking mode
        
    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   temperature: float = 0.7,
                   max_tokens: int = 2000,
                   stream: bool = False,
                   json_mode: bool = False,
                   functions: Optional[List[Dict]] = None,
                   use_reasoning: bool = False) -> Optional[str]:
        """
        Отправляет запрос к DeepSeek API
        
        Args:
            messages: Список сообщений [{"role": "user/assistant/system", "content": "..."}]
            temperature: Температура генерации (0.0-2.0)
            max_tokens: Максимум токенов в ответе
            stream: Потоковая отправка ответа
            json_mode: Включить JSON режим вывода
            functions: Список функций для function calling
            use_reasoning: Использовать deepseek-reasoner (thinking mode)
            
        Returns:
            Ответ от модели или None в случае ошибки
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Выбор модели
        model = self.reasoning_model if use_reasoning else self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        # JSON mode
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        # Function calling
        if functions:
            payload["functions"] = functions
            payload["function_call"] = "auto"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)  # Больше для reasoning
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Проверяем наличие reasoning content (для deepseek-reasoner)
                        message = data['choices'][0]['message']
                        
                        # Если есть function_call - возвращаем весь message для обработки
                        if 'function_call' in message:
                            return message
                        
                        if 'reasoning_content' in message and message['reasoning_content']:
                            # Reasoning mode - возвращаем и процесс мышления, и ответ
                            reasoning = message['reasoning_content']
                            content = message.get('content', '')
                            return f"🤔 Процесс рассуждения:\n{reasoning}\n\n💡 Ответ:\n{content}"
                        else:
                            # Обычный режим
                            return message.get('content')
                    else:
                        error_text = await response.text()
                        print(f"❌ DeepSeek API Error: {response.status} - {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            print("❌ DeepSeek API Timeout")
            return None
        except Exception as e:
            print(f"❌ DeepSeek API Exception: {e}")
            return None
    
    async def chat_with_context(self, user_message: str, 
                                context_messages: List[Dict[str, str]],
                                system_prompt: str = None) -> Optional[str]:
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
        
        # Добавляем системный промпт
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
        
        return await self.chat(messages)
    
    async def summarize_text(self, text: str) -> Optional[str]:
        """Создает краткое резюме текста"""
        messages = [
            {"role": "system", "content": "Ты помощник, который делает краткие выжимки текста на русском языке."},
            {"role": "user", "content": f"Сделай краткую выжимку этого текста:\n\n{text}"}
        ]
        return await self.chat(messages, temperature=0.3)
    
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
    
    async def reasoning_chat(self, user_message: str, 
                            context_messages: List[Dict[str, str]] = None,
                            system_prompt: str = None) -> Optional[str]:
        """
        Использует deepseek-reasoner (thinking mode) для сложных задач
        Показывает процесс рассуждения модели
        
        Args:
            user_message: Вопрос или задача
            context_messages: История (опционально)
            system_prompt: Системный промпт
            
        Returns:
            Ответ с процессом рассуждения
        """
        messages = []
        
        # Системный промпт
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system", 
                "content": "Ты помощник, который тщательно анализирует задачи и показывает процесс рассуждения."
            })
        
        # Контекст
        if context_messages:
            for msg in context_messages[-5:]:  # Меньше для reasoning
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Вопрос
        messages.append({"role": "user", "content": user_message})
        
        # Используем reasoning mode
        return await self.chat(messages, temperature=0.7, use_reasoning=True, max_tokens=4000)
    
    async def extract_json(self, text: str, schema_description: str) -> Optional[Dict]:
        """
        Извлекает структурированные данные в JSON формате
        
        Args:
            text: Текст для анализа
            schema_description: Описание нужной структуры данных
            
        Returns:
            Словарь с извлеченными данными
        """
        messages = [
            {
                "role": "system",
                "content": f"Извлеки из текста данные и верни в JSON формате. Структура: {schema_description}"
            },
            {"role": "user", "content": text}
        ]
        
        response = await self.chat(messages, temperature=0.1, json_mode=True, max_tokens=1000)
        
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                print("❌ Ошибка парсинга JSON ответа")
                return None
        return None
    
    async def analyze_with_reasoning(self, task: str, data: str = None) -> Optional[str]:
        """
        Глубокий анализ с использованием reasoning mode
        Полезно для сложных задач: код ревью, анализ данных, принятие решений
        
        Args:
            task: Описание задачи
            data: Данные для анализа (опционально)
            
        Returns:
            Детальный анализ с рассуждениями
        """
        prompt = task
        if data:
            prompt += f"\n\nДанные:\n{data}"
        
        messages = [
            {
                "role": "system",
                "content": "Ты эксперт-аналитик. Тщательно рассуждай над задачей, рассматривай разные варианты и приходи к взвешенному решению."
            },
            {"role": "user", "content": prompt}
        ]
        
        return await self.chat(messages, temperature=0.6, use_reasoning=True, max_tokens=4000)

