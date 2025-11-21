"""
Гибридный AI сервис - умный выбор модели для каждой задачи

Архитектура:
- ChatGPT (gpt-4o-mini) -> балансирующая модель
- Gemini 2.0 Flash -> быстрые ответы, vision
- DeepSeek Reasoner -> сложные задачи, анализ

Все модели представляют единую личность AIVE!
"""
from typing import List, Dict, Optional, Literal
from services.ai_service import AIService
from services.gemini_service import GeminiService
from services.openai_service import OpenAIService
from services.aive_personality import AIVEPersonality
from services.emotional_intelligence import EmotionalIntelligence
import config


TaskType = Literal["general", "reasoning", "emotional", "vision", "extraction", "creative", "professional"]


class HybridAIService:
    """
    Умный AI сервис который выбирает лучшую модель для задачи
    
    Все модели представляют единую личность AIVE!
    
    Преимущества:
    - Оптимальные траты (умный выбор модели)
    - Лучшее качество для каждой задачи
    - Единая личность AIVE
    - Автоматический fallback
    """
    
    def __init__(self, db=None):
        # Инициализация моделей
        self.chatgpt = OpenAIService()
        self.gemini = GeminiService()
        self.deepseek = AIService()
        
        # Единая личность AIVE
        self.personality = AIVEPersonality()
        
        # Эмоциональный интеллект
        self.emotional = EmotionalIntelligence(db=db)
        
        # Статистика использования (для оптимизации)
        self.usage_stats = {
            "chatgpt": 0,
            "gemini": 0,
            "deepseek": 0,
            "fallbacks": 0,
            "emotional_adaptations": 0
        }
        
        # Логируем доступные модели
        available = []
        if self.chatgpt.is_available():
            available.append("ChatGPT")
        if self.gemini.is_available():
            available.append("Gemini")
        if self.deepseek:
            available.append("DeepSeek")
        
        print(f"🤖 AIVE инициализирован с моделями: {', '.join(available)}")
        print(f"💙 Эмоциональный интеллект: активирован")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        task_type: TaskType = "general",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        user_id: Optional[int] = None,
        functions: List[Dict] = None
    ) -> Optional[str]:
        """
        Умный чат с автоматическим выбором модели и эмоциональным интеллектом
        
        Args:
            messages: Список сообщений
            task_type: Тип задачи для выбора модели
            temperature: Температура генерации
            max_tokens: Максимум токенов
            user_id: ID пользователя (для эмоционального анализа)
            functions: Список функций для вызова (опционально)
        
        Returns:
            Ответ AI или None
        """
        # Если передан user_id и последнее сообщение от пользователя - анализируем эмоцию
        processed_messages = messages[:]
        
        if user_id is not None and messages:
            last_message = messages[-1]
            if last_message.get("role") == "user":
                user_text = last_message.get("content", "")
                
                # Анализ эмоции
                emotion_analysis = self.emotional.analyze_emotion(user_text)
                
                # Сохраняем эмоцию
                await self.emotional.save_emotion_record(user_id, user_text, emotion_analysis)
                
                # Если эмоция сильная - адаптируем системный промпт
                if emotion_analysis["emotion"] != "neutral" and emotion_analysis["confidence"] > 0.5:
                    emotional_instructions = self.emotional.get_response_instructions(emotion_analysis)
                    
                    # Добавляем/обновляем системный промпт
                    system_found = False
                    for msg in processed_messages:
                        if msg["role"] == "system":
                            msg["content"] = f"{msg['content']}\n\n{emotional_instructions}"
                            system_found = True
                            break
                    
                    if not system_found:
                        processed_messages.insert(0, {
                            "role": "system",
                            "content": emotional_instructions
                        })
                    
                    self.usage_stats["emotional_adaptations"] += 1
        
        # Выбираем модель на основе типа задачи
        model_name = self._select_model(task_type)
        
        # Пробуем выбранную модель
        response = await self._try_model(
            model_name,
            processed_messages,
            temperature,
            max_tokens,
            functions=functions
        )
        
        # Если не удалось - пробуем fallback
        if response is None:
            response = await self._fallback_chat(processed_messages, temperature, max_tokens)
        
        return response
    
    async def chat_with_context(
        self,
        user_id: int,
        user_message: str,
        context_messages: List[Dict[str, str]],
        system_prompt: str = None,
        task_type: TaskType = "general",
        user_memory: str = None
    ) -> Optional[str]:
        """
        Чат с контекстом, эмоциональным интеллектом и умным выбором модели
        Все модели используют единую личность AIVE!
        
        Args:
            user_id: ID пользователя
            user_message: Новое сообщение
            context_messages: История
            system_prompt: Системный промпт (опционально)
            task_type: Тип задачи
            user_memory: Память о пользователе
        
        Returns:
            Ответ AI от имени AIVE с эмоциональной адаптацией
        """
        # 1. Анализ эмоции в сообщении
        emotion_analysis = self.emotional.analyze_emotion(user_message)
        
        # Сохраняем эмоциональную запись
        await self.emotional.save_emotion_record(user_id, user_message, emotion_analysis)
        
        # 2. Определяем тип задачи автоматически если не указан
        if task_type == "general":
            task_type = self._detect_task_type(user_message, context_messages)
        
        # 3. Выбираем модель
        model_name = self._select_model(task_type)
        
        # 4. Создаем AIVE-промпт с эмоциональной адаптацией
        if not system_prompt:
            context_type_map = {
                "emotional": "emotional",
                "reasoning": "reasoning",
                "creative": "creative",
                "professional": "professional",
                "general": "casual"
            }
            context_type = context_type_map.get(task_type, "casual")
            
            # Базовый промпт от AIVE
            base_prompt = self.personality.get_system_prompt(
                context_type=context_type,
                user_memory=user_memory
            )
            
            # Добавляем эмоциональный контекст
            if emotion_analysis["emotion"] != "neutral" and emotion_analysis["confidence"] > 0.5:
                emotional_instructions = self.emotional.get_response_instructions(emotion_analysis)
                system_prompt = f"{base_prompt}\n\n{emotional_instructions}"
                self.usage_stats["emotional_adaptations"] += 1
            else:
                system_prompt = base_prompt
        
        # 5. Формируем сообщения
        messages = []
        
        # Системный промпт (AIVE + эмоциональная адаптация!)
        messages.append({"role": "system", "content": system_prompt})
        
        # Контекст
        for msg in context_messages[-config.MAX_CONTEXT_MESSAGES:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Новое сообщение
        messages.append({"role": "user", "content": user_message})
        
        # 6. Отправляем запрос к выбранной модели
        if model_name == "chatgpt" and self.chatgpt.is_available():
            response = await self.chatgpt.chat(messages, 0.7, 2000)
            if response:
                self.usage_stats["chatgpt"] += 1
                return response
        
        elif model_name == "gemini" and self.gemini.is_available():
            response = await self.gemini.chat(messages, 0.7, 2000)
            if response:
                self.usage_stats["gemini"] += 1
                return response
        
        elif model_name == "deepseek":
            response = await self.deepseek.chat(messages, 0.7, 2000)
            if response:
                self.usage_stats["deepseek"] += 1
                return response
        
        # Fallback
        return await self._fallback_chat(messages, 0.7, 2000)
    
    async def reasoning_chat(
        self,
        user_message: str,
        context_messages: List[Dict[str, str]] = None,
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Reasoning mode - всегда использует DeepSeek Reasoner
        
        Args:
            user_message: Вопрос или задача
            context_messages: История (опционально)
            system_prompt: Системный промпт
        
        Returns:
            Ответ с процессом рассуждения
        """
        self.usage_stats["deepseek"] += 1
        return await self.deepseek.reasoning_chat(
            user_message,
            context_messages,
            system_prompt
        )
    
    async def analyze_with_image(
        self,
        text: str,
        image_data: bytes,
        mime_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Анализ изображения - использует Gemini (лучшее vision)
        
        Args:
            text: Текстовый промпт
            image_data: Байты изображения
            mime_type: MIME тип
        
        Returns:
            Ответ с анализом
        """
        self.usage_stats["gemini"] += 1
        return await self.gemini.analyze_with_image(text, image_data, mime_type)
    
    async def extract_json(
        self,
        text: str,
        schema_description: str
    ) -> Optional[Dict]:
        """
        Извлечение JSON - использует Gemini (быстрый и точный)
        
        Args:
            text: Текст для анализа
            schema_description: Описание структуры
        
        Returns:
            Словарь с данными
        """
        self.usage_stats["gemini"] += 1
        return await self.gemini.extract_json(text, schema_description)
    
    async def summarize_text(self, text: str) -> Optional[str]:
        """Резюмирование - Gemini (быстро и бесплатно)"""
        self.usage_stats["gemini"] += 1
        return await self.gemini.summarize_text(text)
    
    async def extract_facts(self, text: str) -> Optional[str]:
        """Извлечение фактов - Gemini"""
        self.usage_stats["gemini"] += 1
        return await self.gemini.extract_facts(text)
    
    def _select_model(self, task_type: TaskType) -> str:
        """
        Выбирает лучшую модель для типа задачи
        
        Стратегия:
        - ChatGPT: эмоции, креатив, профессиональное (лучшее качество)
        - Gemini: обычное, vision, extraction (быстро + экономно)
        - DeepSeek: reasoning (специализация)
        
        Args:
            task_type: Тип задачи
        
        Returns:
            Имя модели: "chatgpt", "gemini", "deepseek"
        """
        if task_type == "reasoning":
            # Сложная задача -> DeepSeek Reasoner
            return "deepseek"
        
        elif task_type == "emotional":
            # Эмоциональная поддержка -> ChatGPT (эмпатичный)
            return "chatgpt"
        
        elif task_type == "creative":
            # Креативность -> ChatGPT (лучший для генерации идей)
            return "chatgpt"
        
        elif task_type == "professional":
            # Профессиональный контекст -> ChatGPT (структурированный)
            return "chatgpt"
        
        elif task_type == "vision":
            # Анализ изображений -> Gemini (отличное vision)
            return "gemini"
        
        elif task_type == "extraction":
            # Извлечение данных -> Gemini (быстрый + точный)
            return "gemini"
        
        else:  # general
            # Обычный диалог -> Gemini (экономно)
            # Но если Gemini недоступен -> ChatGPT
            return "gemini" if self.gemini.is_available() else "chatgpt"
    
    def _detect_task_type(
        self,
        user_message: str,
        context_messages: List[Dict[str, str]]
    ) -> TaskType:
        """
        Автоматически определяет тип задачи по сообщению
        Использует AIVE personality для детекции
        
        Args:
            user_message: Сообщение пользователя
            context_messages: История для контекста
        
        Returns:
            Тип задачи
        """
        # Используем детектор из AIVEPersonality
        context_type = self.personality.detect_context_type(user_message)
        
        # Мапим на TaskType
        mapping = {
            "emotional": "emotional",
            "reasoning": "reasoning",
            "creative": "creative",
            "professional": "professional",
            "casual": "general"
        }
        
        return mapping.get(context_type, "general")
    
    async def _try_model(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        functions: Optional[List[Dict]] = None
    ) -> Optional[str]:
        """
        Пробует отправить запрос к конкретной модели
        
        Args:
            model_name: Имя модели
            messages: Сообщения
            temperature: Температура
            max_tokens: Максимум токенов
            functions: Функции для вызова (только для DeepSeek)
        
        Returns:
            Ответ или None
        """
        try:
            if model_name == "chatgpt" and self.chatgpt.is_available():
                response = await self.chatgpt.chat(messages, temperature, max_tokens)
                if response:
                    self.usage_stats["chatgpt"] += 1
                    return response
            
            elif model_name == "gemini" and self.gemini.is_available():
                response = await self.gemini.chat(messages, temperature, max_tokens)
                if response:
                    self.usage_stats["gemini"] += 1
                    return response
            
            elif model_name == "deepseek":
                # DeepSeek поддерживает function calling
                response = await self.deepseek.chat(
                    messages, 
                    temperature, 
                    max_tokens,
                    functions=functions
                )
                if response:
                    self.usage_stats["deepseek"] += 1
                    return response
        
        except Exception as e:
            print(f"❌ Model {model_name} error: {e}")
        
        return None
    
    async def _fallback_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """
        Fallback strategy: пробует модели по порядку
        
        Приоритет: ChatGPT -> Gemini -> DeepSeek
        
        Args:
            messages: Сообщения
            temperature: Температура
            max_tokens: Максимум токенов
        
        Returns:
            Ответ или None
        """
        self.usage_stats["fallbacks"] += 1
        
        # 1. Пробуем ChatGPT
        if self.chatgpt.is_available():
            response = await self._try_model("chatgpt", messages, temperature, max_tokens)
            if response:
                return response
        
        # 2. Пробуем Gemini
        if self.gemini.is_available():
            response = await self._try_model("gemini", messages, temperature, max_tokens)
            if response:
                return response
        
        # 3. Пробуем DeepSeek
        response = await self._try_model("deepseek", messages, temperature, max_tokens)
        if response:
            return response
        
        # Все модели недоступны
        print("❌ Все AI модели недоступны!")
        return self.personality.get_error_message()
    
    def get_usage_stats(self) -> Dict:
        """Возвращает статистику использования моделей"""
        return self.usage_stats.copy()
    
    def reset_usage_stats(self):
        """Сбрасывает статистику использования"""
        self.usage_stats = {
            "gemini": 0,
            "deepseek": 0,
            "claude": 0,
            "fallbacks": 0
        }

