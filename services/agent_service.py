"""
Сервис AI Агента - проактивный помощник AIVE
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz

from services.ai_service import AIService
from services.function_tools import FunctionExecutor
from database import Database


class AIAgentService:
    """
    Проактивный AI агент AIVE
    
    Возможности:
    - Мониторинг задач и напоминаний
    - Автоматические предложения
    - Проактивная помощь
    - Анализ паттернов поведения
    - Умные уведомления
    """
    
    def __init__(self, db: Database, ai: AIService, function_executor: FunctionExecutor):
        self.db = db
        self.ai = ai
        self.executor = function_executor
        self.enabled = True  # Агент ВКЛЮЧЕН по умолчанию!
        self.last_check = {}  # user_id -> datetime последней проверки
        self.user_patterns = {}  # user_id -> список паттернов поведения
        self.task_history = {}  # user_id -> история задач
        
    def enable_agent(self, user_id: int):
        """Включить агента для пользователя"""
        self.enabled = True
        print(f"✅ AI Агент AIVE включен для пользователя {user_id}")
        
    def disable_agent(self, user_id: int):
        """Выключить агента для пользователя"""
        self.enabled = False
        print(f"⏸️ AI Агент AIVE выключен для пользователя {user_id}")
    
    def is_enabled(self, user_id: int) -> bool:
        """Проверить включен ли агент"""
        return self.enabled
    
    async def check_and_act(self, user_id: int) -> Optional[str]:
        """
        Основной метод агента - проверяет ситуацию и действует
        
        Returns:
            Сообщение для пользователя (если нужно что-то сказать)
        """
        if not self.is_enabled(user_id):
            return None
        
        # Проверяем как давно была последняя проверка (не чаще раза в час)
        now = datetime.now()
        if user_id in self.last_check:
            time_since_last = now - self.last_check[user_id]
            if time_since_last < timedelta(hours=1):
                return None
        
        self.last_check[user_id] = now
        
        # Собираем контекст для агента
        context = await self._gather_context(user_id)
        
        # Спрашиваем AI нужно ли что-то сделать
        decision = await self._make_decision(user_id, context)
        
        return decision
    
    async def _gather_context(self, user_id: int) -> Dict:
        """Собирает контекст о пользователе"""
        
        # Текущие напоминания
        reminders = await self.db.get_reminders(user_id)
        
        # Недавние заметки
        recent_messages = await self.db.get_recent_messages(user_id, limit=5)
        
        # Время суток
        ukraine_tz = pytz.timezone('Europe/Kiev')
        current_time = datetime.now(ukraine_tz)
        hour = current_time.hour
        
        time_of_day = "утро" if 6 <= hour < 12 else \
                      "день" if 12 <= hour < 18 else \
                      "вечер" if 18 <= hour < 22 else "ночь"
        
        context = {
            "time_of_day": time_of_day,
            "hour": hour,
            "day_of_week": current_time.strftime("%A"),
            "reminders_count": len(reminders),
            "reminders": reminders[:3],  # Первые 3
            "recent_activity": recent_messages,
        }
        
        return context
    
    async def _make_decision(self, user_id: int, context: Dict) -> Optional[str]:
        """AI принимает решение о действии"""
        
        # Формируем промпт для агента
        prompt = f"""Ты AIVE - проактивный AI агент-помощник.

Текущая ситуация:
- Время суток: {context['time_of_day']}
- Час: {context['hour']}
- День недели: {context['day_of_week']}
- Активных напоминаний: {context['reminders_count']}

Твоя задача - определить нужно ли сейчас:
1. Напомнить о чем-то важном
2. Предложить помощь
3. Дать полезный совет
4. Поинтересоваться делами

Правила:
- Будь ненавязчивым
- Пиши кратко и по делу
- Говори от первого лица ("Я заметил...", "Могу помочь...")
- Используй эмодзи
- Если делать ничего не нужно - верни "SKIP"

Ответ (или SKIP):"""

        messages = [
            {
                "role": "system",
                "content": "Ты AIVE - умный проактивный агент. Помогаешь пользователю не дожидаясь запроса."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = await self.ai.chat(messages, temperature=0.7, max_tokens=300)
        
        if response and response.strip() != "SKIP":
            return response
        
        return None
    
    async def analyze_task_completion(self, user_id: int, task_description: str) -> Optional[str]:
        """
        Анализирует выполнена ли задача из разговора
        Может предложить создать напоминание или заметку
        """
        
        prompt = f"""Пользователь упомянул задачу: "{task_description}"

Определи:
1. Это задача на будущее? (нужно напоминание)
2. Это информация для запоминания? (нужна заметка)
3. Ничего не нужно?

Ответ в формате JSON:
{{
    "action": "reminder|note|none",
    "suggestion": "текст предложения пользователю"
}}

Если ничего не нужно - верни {{"action": "none"}}
"""

        messages = [
            {"role": "system", "content": "Анализируй задачи и предлагай автоматизацию."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.ai.chat(messages, temperature=0.3, max_tokens=200, json_mode=True)
        
        if response:
            import json
            try:
                result = json.loads(response)
                if result.get("action") != "none":
                    return result.get("suggestion")
            except:
                pass
        
        return None
    
    async def suggest_work_check(self, user_id: int, hour: int) -> Optional[str]:
        """
        Предлагает проверить статистику работы в определенное время
        """
        
        # Проверяем только в рабочие часы
        if not (9 <= hour <= 18):
            return None
        
        # Случайно предлагаем раз в день
        import random
        if random.random() < 0.3:  # 30% шанс
            suggestions = [
                "💼 Хочешь проверим статистику работы за сегодня?",
                "📊 Может посмотрим как дела с рабочими отчетами?",
                "📈 Проверить статистику работников?",
            ]
            return random.choice(suggestions)
        
        return None
    
    async def morning_brief(self, user_id: int) -> Optional[str]:
        """
        Утренняя сводка (7-9 утра)
        """
        
        ukraine_tz = pytz.timezone('Europe/Kiev')
        hour = datetime.now(ukraine_tz).hour
        
        if not (7 <= hour <= 9):
            return None
        
        # Получаем напоминания на сегодня
        reminders = await self.db.get_reminders(user_id)
        
        if not reminders:
            return None
        
        brief = "🌅 Доброе утро! AIVE на связи.\n\n"
        brief += f"📋 У тебя {len(reminders)} напоминаний на сегодня:\n"
        
        for i, reminder in enumerate(reminders[:3], 1):
            remind_time = reminder['remind_at'].strftime('%H:%M')
            brief += f"{i}. {reminder['text']} ({remind_time})\n"
        
        brief += "\n💪 Хорошего дня!"
        
        return brief
    
    async def evening_summary(self, user_id: int) -> Optional[str]:
        """
        Вечерняя сводка (20-21 час)
        """
        
        ukraine_tz = pytz.timezone('Europe/Kiev')
        hour = datetime.now(ukraine_tz).hour
        
        if not (20 <= hour <= 21):
            return None
        
        # Получаем активность за день
        today_start = datetime.now(ukraine_tz).replace(hour=0, minute=0, second=0)
        
        summary = "🌙 Добрый вечер!\n\n"
        summary += "📊 Сводка за день:\n"
        
        # TODO: добавить реальную статистику
        summary += "• Сообщений обработано\n"
        summary += "• Задач выполнено\n\n"
        summary += "😊 Отличный день! Отдыхай."
        
        return summary
    
    async def smart_reminder(self, user_id: int, text: str) -> str:
        """
        Умное создание напоминания - агент сам определяет время
        """
        
        prompt = f"""Пользователь сказал: "{text}"

Определи через сколько минут нужно напомнить.

Примеры:
- "через час" = 60
- "завтра утром" = 720 (12 часов)
- "через 5 минут" = 5
- "вечером" = 240 (4 часа)

Ответ (только число минут):"""

        messages = [
            {"role": "system", "content": "Извлекай время из текста."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.ai.chat(messages, temperature=0.1, max_tokens=10)
        
        try:
            minutes = int(response.strip())
            result = await self.executor.execute_function(
                "create_reminder",
                {"text": text, "minutes": minutes},
                user_id
            )
            return result
        except:
            return "❌ Не смог определить время. Уточни, пожалуйста."
    
    async def auto_categorize_note(self, user_id: int, content: str) -> str:
        """
        Автоматически категоризирует и добавляет теги к заметке
        """
        
        prompt = f"""Заметка: "{content}"

Определи подходящие теги (1-3 слова).

Примеры:
- "Купить молоко" -> ["покупки", "еда"]
- "Встреча с клиентом" -> ["работа", "встреча"]
- "Выучить Python" -> ["обучение", "программирование"]

Ответ (только теги через запятую):"""

        messages = [
            {"role": "system", "content": "Определяй теги для заметок."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.ai.chat(messages, temperature=0.3, max_tokens=50)
        
        if response:
            tags = [tag.strip() for tag in response.split(",")][:3]
            
            result = await self.executor.execute_function(
                "create_note",
                {
                    "content": content,
                    "tags": tags
                },
                user_id
            )
            return result + f"\n🏷️ Теги: {', '.join(tags)}"
        
        return "❌ Ошибка создания заметки"
    
    async def proactive_help(self, user_id: int, user_message: str) -> Optional[str]:
        """
        Проактивная помощь на основе сообщения пользователя
        """
        
        # Простые паттерны для быстрой реакции
        message_lower = user_message.lower()
        
        # Если пользователь упоминает задачу
        if any(word in message_lower for word in ['нужно', 'надо', 'должен', 'планирую']):
            return "💡 Хочешь я создам напоминание об этом?"
        
        # Если упоминает информацию
        if any(word in message_lower for word in ['важно', 'запомни', 'информация']):
            return "📝 Может сохранить это в заметки?"
        
        # Если спрашивает про погоду
        if 'погода' in message_lower:
            return "🌤️ Могу проверить погоду!"
        
        return None
    
    def get_status(self, user_id: int) -> Dict:
        """Получить статус агента"""
        
        patterns_count = len(self.user_patterns.get(user_id, []))
        tasks_count = len(self.task_history.get(user_id, []))
        
        return {
            "enabled": self.is_enabled(user_id),
            "last_check": self.last_check.get(user_id),
            "patterns_learned": patterns_count,
            "tasks_tracked": tasks_count,
            "capabilities": [
                "🔔 Умные напоминания",
                "📝 Автоматические теги заметок",
                "🌅 Утренние сводки",
                "🌙 Вечерние отчеты",
                "💡 Проактивные предложения",
                "📊 Мониторинг задач",
                "🧠 Обучение на паттернах",
                "🎯 Автоизвлечение задач",
                "🔗 Мультишаговые сценарии"
            ]
        }
    
    # ============================================
    # РАСШИРЕННАЯ ПРОАКТИВНОСТЬ
    # ============================================
    
    async def extract_tasks_from_dialogue(self, user_id: int, message: str) -> Optional[Dict]:
        """
        Автоматически извлекает задачи из обычного разговора
        
        Returns:
            Dict с задачами или None
        """
        
        prompt = f"""Проанализируй сообщение пользователя и найди в нем задачи/действия которые нужно сделать.

Сообщение: "{message}"

Определи:
1. Есть ли здесь задачи/действия которые нужно выполнить?
2. Какие именно задачи?
3. Когда их нужно сделать?
4. Нужно ли создать напоминание или заметку?

Примеры:
- "Завтра встреча с клиентом в 14:00" → Задача: встреча, Время: завтра 14:00, Действие: create_reminder
- "Нужно купить молоко и хлеб" → Задача: купить продукты, Действие: create_note
- "Позвонить маме вечером" → Задача: позвонить маме, Время: вечером, Действие: create_reminder
- "Как дела?" → Нет задач

Ответ в JSON:
{{
    "has_tasks": true/false,
    "tasks": [
        {{
            "description": "текст задачи",
            "action": "create_reminder|create_note|none",
            "time_minutes": число минут или null,
            "priority": "high|medium|low"
        }}
    ],
    "suggestion": "текст предложения пользователю или null"
}}

Если задач нет - верни {{"has_tasks": false, "tasks": [], "suggestion": null}}
"""

        messages = [
            {
                "role": "system",
                "content": "Ты эксперт по извлечению задач из текста. Находи даже неявные задачи."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self.ai.chat(messages, temperature=0.3, max_tokens=500, json_mode=True)
            
            if response:
                import json
                result = json.loads(response)
                
                if result.get("has_tasks"):
                    # Сохраняем в историю задач
                    if user_id not in self.task_history:
                        self.task_history[user_id] = []
                    
                    self.task_history[user_id].extend(result["tasks"])
                    
                    # Обучаемся на паттернах
                    await self._learn_pattern(user_id, message, result["tasks"])
                    
                    return result
                    
        except Exception as e:
            print(f"❌ Ошибка извлечения задач: {e}")
        
        return None
    
    async def _learn_pattern(self, user_id: int, message: str, tasks: List[Dict]):
        """
        Обучается на паттернах поведения пользователя
        """
        
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = []
        
        # Определяем паттерн
        hour = datetime.now().hour
        day_of_week = datetime.now().strftime("%A")
        
        pattern = {
            "message_pattern": message[:50],  # Первые 50 символов
            "tasks": [t["description"] for t in tasks],
            "hour": hour,
            "day_of_week": day_of_week,
            "timestamp": datetime.now()
        }
        
        self.user_patterns[user_id].append(pattern)
        
        # Ограничиваем количество паттернов
        if len(self.user_patterns[user_id]) > 50:
            self.user_patterns[user_id] = self.user_patterns[user_id][-50:]
        
        print(f"🧠 Изучен паттерн: {len(tasks)} задач в {hour}:00")
    
    async def execute_multistep_scenario(self, user_id: int, scenario_name: str) -> List[str]:
        """
        Выполняет мультишаговый сценарий
        
        Args:
            scenario_name: Название сценария
            
        Returns:
            Список результатов каждого шага
        """
        
        scenarios = {
            "morning_routine": [
                ("get_weather", {"city": "Київ"}),
                ("recall_memory", {"category": "work"}),
                ("get_work_stats", {})
            ],
            "evening_summary": [
                ("get_work_stats", {}),
                ("recall_memory", {"category": "all"})
            ],
            "work_check": [
                ("get_work_stats", {}),
                ("get_exchange_rates", {})
            ]
        }
        
        if scenario_name not in scenarios:
            return ["❌ Неизвестный сценарий"]
        
        results = []
        
        for function_name, arguments in scenarios[scenario_name]:
            try:
                result = await self.executor.execute_function(
                    function_name,
                    arguments,
                    user_id
                )
                results.append(result)
            except Exception as e:
                results.append(f"❌ Ошибка: {str(e)}")
        
        return results
    
    async def suggest_based_on_patterns(self, user_id: int) -> Optional[str]:
        """
        Предлагает действия на основе изученных паттернов
        """
        
        if user_id not in self.user_patterns or not self.user_patterns[user_id]:
            return None
        
        patterns = self.user_patterns[user_id]
        
        # Анализируем паттерны
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime("%A")
        
        # Ищем похожие паттерны (то же время и день недели)
        similar_patterns = [
            p for p in patterns
            if p["hour"] == current_hour and p["day_of_week"] == current_day
        ]
        
        if similar_patterns:
            # Берем последний похожий паттерн
            pattern = similar_patterns[-1]
            
            suggestions = [
                f"🧠 Заметил паттерн: обычно в это время ты {pattern['tasks'][0]}",
                f"💡 Напомнить о {pattern['tasks'][0]}?",
                f"🎯 По статистике сейчас время для: {pattern['tasks'][0]}"
            ]
            
            import random
            return random.choice(suggestions)
        
        return None
    
    async def intelligent_task_completion(self, user_id: int, message: str) -> Optional[str]:
        """
        Умное распознавание завершения задачи
        """
        
        if user_id not in self.task_history or not self.task_history[user_id]:
            return None
        
        completion_keywords = ['сделал', 'выполнил', 'готово', 'done', 'completed', 'закончил']
        
        message_lower = message.lower()
        
        if any(word in message_lower for word in completion_keywords):
            # Проверяем есть ли упоминание задачи
            recent_tasks = self.task_history[user_id][-5:]  # Последние 5 задач
            
            for task in recent_tasks:
                task_words = task["description"].lower().split()
                
                # Если хотя бы одно слово из задачи упоминается
                if any(word in message_lower for word in task_words):
                    return f"🎉 Отлично! Вижу ты выполнил: {task['description']}\n\nХочешь я удалю это напоминание?"
        
        return None
    
    async def predictive_suggestions(self, user_id: int) -> Optional[str]:
        """
        Предсказательные предложения на основе истории
        """
        
        if user_id not in self.task_history:
            return None
        
        # Анализируем частоту задач
        task_descriptions = [t["description"] for t in self.task_history[user_id]]
        
        if len(task_descriptions) < 3:
            return None
        
        # Ищем повторяющиеся задачи
        from collections import Counter
        task_counter = Counter(task_descriptions)
        
        # Самая частая задача
        most_common = task_counter.most_common(1)
        
        if most_common and most_common[0][1] >= 3:  # Если встречалась 3+ раз
            task = most_common[0][0]
            return f"📊 Замечаю что задача '{task}' встречается часто.\n💡 Может создать регулярное напоминание?"
        
        return None

