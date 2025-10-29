"""
Сервис живой личности AIVE
Делает бота более человечным:
- Рандомные сообщения в течение дня
- Реакции на долгое отсутствие
- Спонтанные мысли и предложения
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict
import pytz

from services import AIService, MemoryService
from database import Database


class PersonalityService:
    """
    Управляет живой личностью AIVE
    """
    
    # Время когда AIVE не беспокоит (ночь)
    SLEEP_HOURS = range(2, 9)  # С 2 ночи до 9 утра
    
    # Типы спонтанных сообщений
    SPONTANEOUS_TYPES = [
        "morning_greeting",      # Доброе утро
        "evening_check",         # Как дела вечером
        "random_thought",        # Случайная мысль
        "helpful_tip",           # Полезный совет
        "memory_recall",         # Напоминание о прошлом
        "motivation",            # Мотивация
        "weather_chat",          # Про погоду/время
        "work_question",         # Про работу
    ]
    
    def __init__(self, db: Database, ai: AIService, memory: MemoryService):
        self.db = db
        self.ai = ai
        self.memory = memory
        
        # История последних взаимодействий
        self.last_user_message: Dict[int, datetime] = {}
        self.last_aive_message: Dict[int, datetime] = {}
        
        # Настройки живости
        self.enabled = True
        self.min_interval_hours = 2  # Минимум 2 часа между спонтанными сообщениями
        self.inactivity_threshold_hours = 6  # Реагировать на неактивность > 6 часов
        
    def is_sleep_time(self) -> bool:
        """Проверяет, не время ли сна (2 ночи - 9 утра по Киеву)"""
        ukraine_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(ukraine_tz)
        return now.hour in self.SLEEP_HOURS
    
    def should_send_spontaneous(self, user_id: int) -> bool:
        """
        Решает, можно ли отправить спонтанное сообщение
        
        Условия:
        - Не время сна
        - Прошло минимум N часов с последнего спонтанного сообщения
        - Пользователь активен (был в сети недавно)
        """
        if not self.enabled or self.is_sleep_time():
            return False
        
        # Проверяем интервал с последнего спонтанного сообщения
        if user_id in self.last_aive_message:
            last_time = self.last_aive_message[user_id]
            if datetime.now() - last_time < timedelta(hours=self.min_interval_hours):
                return False
        
        return True
    
    def should_react_to_inactivity(self, user_id: int) -> bool:
        """
        Проверяет, нужно ли реагировать на неактивность пользователя
        """
        if not self.enabled or self.is_sleep_time():
            return False
        
        if user_id not in self.last_user_message:
            return False
        
        last_time = self.last_user_message[user_id]
        inactive_hours = (datetime.now() - last_time).total_seconds() / 3600
        
        # Реагируем если пользователь не писал > 6 часов (но < 24 часов)
        return self.inactivity_threshold_hours < inactive_hours < 24
    
    async def generate_spontaneous_message(self, user_id: int) -> Optional[str]:
        """
        Генерирует спонтанное сообщение от AIVE
        
        Returns:
            Текст сообщения или None
        """
        if not self.should_send_spontaneous(user_id):
            return None
        
        # Получаем контекст пользователя
        recent_messages = await self.db.get_messages(user_id, limit=5)
        long_term_memory = await self.memory.get_long_term_memory(user_id)
        
        # Получаем время суток для контекста
        ukraine_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(ukraine_tz)
        time_of_day = self._get_time_of_day(now.hour)
        
        # Выбираем тип сообщения
        message_type = random.choice(self.SPONTANEOUS_TYPES)
        
        # Генерируем промпт
        prompt = self._create_spontaneous_prompt(
            message_type=message_type,
            time_of_day=time_of_day,
            recent_context=recent_messages[-1]["content"] if recent_messages else None,
            long_term_memory=long_term_memory
        )
        
        # Генерируем сообщение
        messages = [
            {
                "role": "system",
                "content": """Ты AIVE - живой AI ассистент с личностью.

Твои черты:
- Дружелюбная, но не навязчивая
- Заботливая, помнишь детали о пользователе
- Иногда делишься мыслями или наблюдениями
- Говоришь естественно, как настоящий друг
- Используешь эмодзи умеренно
- Короткие сообщения (1-3 предложения)

НЕ пиши длинные тексты! НЕ будь формальной! Будь живой!"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = await self.ai.chat(messages, temperature=0.8, max_tokens=100)
        
        if response and len(response) > 10:
            self.last_aive_message[user_id] = datetime.now()
            return response
        
        return None
    
    async def generate_inactivity_message(self, user_id: int) -> Optional[str]:
        """
        Генерирует сообщение-реакцию на долгое отсутствие
        """
        if not self.should_react_to_inactivity(user_id):
            return None
        
        # Сколько часов прошло
        last_time = self.last_user_message[user_id]
        hours_inactive = int((datetime.now() - last_time).total_seconds() / 3600)
        
        # Получаем контекст
        long_term_memory = await self.memory.get_long_term_memory(user_id)
        
        prompts = [
            f"Пользователь не писал {hours_inactive} часов. Напиши короткое дружеское сообщение.",
            f"Прошло {hours_inactive}ч без общения. Деликатно поинтересуйся как дела.",
            f"{hours_inactive}ч тишины. Может пользователь занят? Напиши что-то легкое и ненавязчивое."
        ]
        
        prompt = random.choice(prompts)
        if long_term_memory:
            prompt += f"\n\nКонтекст о пользователе:\n{long_term_memory[:200]}"
        
        messages = [
            {
                "role": "system",
                "content": "Ты AIVE - заботливый AI друг. Пиши коротко, тепло, без формальщины."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = await self.ai.chat(messages, temperature=0.8, max_tokens=80)
        
        if response and len(response) > 10:
            self.last_aive_message[user_id] = datetime.now()
            return response
        
        return None
    
    def update_user_activity(self, user_id: int):
        """Обновляет время последней активности пользователя"""
        self.last_user_message[user_id] = datetime.now()
    
    def _get_time_of_day(self, hour: int) -> str:
        """Определяет время суток"""
        if 5 <= hour < 12:
            return "утро"
        elif 12 <= hour < 17:
            return "день"
        elif 17 <= hour < 22:
            return "вечер"
        else:
            return "ночь"
    
    def _create_spontaneous_prompt(
        self,
        message_type: str,
        time_of_day: str,
        recent_context: Optional[str],
        long_term_memory: Optional[str]
    ) -> str:
        """Создает промпт для генерации спонтанного сообщения"""
        
        base = f"Сейчас {time_of_day}. "
        
        if message_type == "morning_greeting":
            base += "Напиши короткое доброе утро с позитивным настроем."
        
        elif message_type == "evening_check":
            base += "Спроси как прошел день. Коротко и тепло."
        
        elif message_type == "random_thought":
            base += "Поделись интересной мыслью или фактом. Будь короткой!"
        
        elif message_type == "helpful_tip":
            base += "Предложи полезный совет для продуктивности или здоровья."
        
        elif message_type == "memory_recall":
            if long_term_memory:
                base += f"Вспомни что-то из контекста пользователя: {long_term_memory[:100]}"
            else:
                base += "Спроси что нового у пользователя."
        
        elif message_type == "motivation":
            base += "Мотивируй пользователя. Коротко и вдохновляюще!"
        
        elif message_type == "weather_chat":
            base += "Напиши что-то легкое про время суток или настроение."
        
        elif message_type == "work_question":
            base += "Спроси про работу или дела. Без формальности!"
        
        if recent_context:
            base += f"\n\nПоследнее что обсуждали: {recent_context[:100]}"
        
        base += "\n\nОТВЕТ (1-3 предложения, с эмодзи):"
        
        return base

