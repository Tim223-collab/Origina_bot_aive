"""
Определение функций (tools) для Function Calling с DeepSeek
"""
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pytz


# Определяем все доступные функции для ИИ
AVAILABLE_FUNCTIONS = [
    {
        "name": "create_reminder",
        "description": "Создать напоминание на определенное время. Используй когда пользователь просит напомнить что-то.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Текст напоминания - что нужно напомнить"
                },
                "minutes": {
                    "type": "integer",
                    "description": "Через сколько минут напомнить (от текущего момента)"
                }
            },
            "required": ["text", "minutes"]
        }
    },
    {
        "name": "create_note",
        "description": "Создать заметку. Используй когда пользователь просит записать, сохранить информацию, добавить заметку.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Содержание заметки"
                },
                "title": {
                    "type": "string",
                    "description": "Заголовок заметки (опционально)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Теги для заметки (опционально)"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "remember_fact",
        "description": "Запомнить важный факт о пользователе в долгосрочную память. Используй когда пользователь говорит о себе (где живёт, чем занимается, что любит и т.д.)",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["personal", "work", "preferences", "learning"],
                    "description": "Категория: personal (личное), work (работа), preferences (предпочтения), learning (обучение)"
                },
                "key": {
                    "type": "string",
                    "description": "Ключ факта (название, что именно запомнить). Например: 'город', 'профессия', 'язык_программирования'"
                },
                "value": {
                    "type": "string",
                    "description": "Значение факта"
                }
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "get_weather",
        "description": "Получить текущую погоду для города. Используй когда пользователь спрашивает про погоду.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Название города для которого нужна погода"
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "get_exchange_rates",
        "description": "Получить курс валют. Используй когда пользователь спрашивает про курс доллара, евро и т.д.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_notes",
        "description": "Найти заметки по ключевому слову. Используй когда пользователь просит найти, показать или вспомнить заметки.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Ключевое слово для поиска"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "recall_memory",
        "description": "Получить факты из долгосрочной памяти. Используй когда нужно вспомнить что-то о пользователе или когда он спрашивает 'что ты знаешь обо мне'.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["personal", "work", "preferences", "learning", "all"],
                    "description": "Категория памяти или 'all' для всех категорий"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_work_stats",
        "description": "Получить РЕАЛЬНУЮ статистику работы сотрудников с сайта через парсинг админ-панели. ОБЯЗАТЕЛЬНО используй эту функцию когда пользователь спрашивает: 'как там сотрудники', 'покажи статистику', 'отчёты работников', 'проверь работников', 'кто отправил отчёт', 'статистика по команде', 'работники отчитались', 'данные по сотрудникам', 'SFS', 'SCH', 'скам у работников'. Эта функция парсит РЕАЛЬНЫЕ данные, а не придумывает их!",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Дата в формате YYYY-MM-DD (опционально, по умолчанию сегодня)"
                },
                "team": {
                    "type": "string",
                    "enum": ["Good Bunny", "Velvet", "all"],
                    "description": "Команда для фильтрации (по умолчанию Good Bunny)"
                }
            },
            "required": []
        }
    },
    {
        "name": "check_worker_scam",
        "description": "Проверить скам у конкретного работника и получить детали с скриншотами. Используй когда пользователь спрашивает про скам конкретного работника (например: 'что со скамом у Алексея', 'покажи отчет по Ивану').",
        "parameters": {
            "type": "object",
            "properties": {
                "worker_name": {
                    "type": "string",
                    "description": "Имя работника для проверки"
                },
                "date": {
                    "type": "string",
                    "description": "Дата в формате YYYY-MM-DD (опционально, по умолчанию сегодня)"
                },
                "team": {
                    "type": "string",
                    "enum": ["Good Bunny", "Velvet", "all"],
                    "description": "Команда (по умолчанию Good Bunny)"
                }
            },
            "required": ["worker_name"]
        }
    }
]


class FunctionExecutor:
    """
    Выполняет функции, которые запрашивает ИИ
    """
    
    def __init__(self, db, memory_service, extras_service, parser_service):
        self.db = db
        self.memory = memory_service
        self.extras = extras_service
        self.parser = parser_service
    
    async def execute_function(self, function_name: str, arguments: Dict[str, Any], user_id: int) -> str:
        """
        Выполняет функцию и возвращает результат
        
        Args:
            function_name: Название функции
            arguments: Аргументы функции (словарь)
            user_id: ID пользователя
            
        Returns:
            Результат выполнения функции (строка для передачи обратно в ИИ)
        """
        
        try:
            if function_name == "create_reminder":
                return await self._create_reminder(user_id, arguments)
            
            elif function_name == "create_note":
                return await self._create_note(user_id, arguments)
            
            elif function_name == "remember_fact":
                return await self._remember_fact(user_id, arguments)
            
            elif function_name == "get_weather":
                return await self._get_weather(arguments)
            
            elif function_name == "get_exchange_rates":
                return await self._get_exchange_rates()
            
            elif function_name == "search_notes":
                return await self._search_notes(user_id, arguments)
            
            elif function_name == "recall_memory":
                return await self._recall_memory(user_id, arguments)
            
            elif function_name == "get_work_stats":
                return await self._get_work_stats(user_id, arguments)
            
            elif function_name == "check_worker_scam":
                return await self._check_worker_scam(user_id, arguments)
            
            else:
                return f"❌ Неизвестная функция: {function_name}"
                
        except Exception as e:
            return f"❌ Ошибка выполнения {function_name}: {str(e)}"
    
    # === РЕАЛИЗАЦИЯ ФУНКЦИЙ ===
    
    async def _create_reminder(self, user_id: int, args: Dict) -> str:
        """Создать напоминание"""
        text = args.get('text')
        minutes = args.get('minutes')
        
        from datetime import timezone
        remind_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        
        reminder_id = await self.db.add_reminder(user_id, text, remind_at)
        
        # Для отображения конвертируем в киевское время
        ukraine_tz = pytz.timezone('Europe/Kiev')
        local_time = remind_at.astimezone(ukraine_tz)
        
        return f"✅ Создано напоминание #{reminder_id}: '{text}' на {local_time.strftime('%H:%M')} (Киев)"
    
    async def _create_note(self, user_id: int, args: Dict) -> str:
        """Создать заметку"""
        content = args.get('content')
        title = args.get('title')
        tags = args.get('tags', [])
        
        note_id = await self.db.add_note(user_id, content, title, tags)
        
        result = f"✅ Заметка #{note_id} создана"
        if title:
            result += f": '{title}'"
        return result
    
    async def _remember_fact(self, user_id: int, args: Dict) -> str:
        """Запомнить факт"""
        category = args.get('category')
        key = args.get('key')
        value = args.get('value')
        
        await self.memory.remember_fact(user_id, category, key, value)
        
        category_ru = {
            'personal': 'личное',
            'work': 'работа',
            'preferences': 'предпочтения',
            'learning': 'обучение'
        }.get(category, category)
        
        return f"✅ Запомнил ({category_ru}): {key} = {value}"
    
    async def _get_weather(self, args: Dict) -> str:
        """Получить погоду"""
        city = args.get('city', 'Київ')
        
        weather = await self.extras.get_weather(city)
        
        if weather.get('error'):
            return f"❌ Не удалось получить погоду: {weather['error']}"
        
        return (
            f"🌤️ Погода в {city}:\n"
            f"🌡️ {weather['temp']}°C (ощущается {weather['feels_like']}°C)\n"
            f"☁️ {weather['description']}\n"
            f"💨 Ветер: {weather['wind_speed']} м/с\n"
            f"💧 Влажность: {weather['humidity']}%"
        )
    
    async def _get_exchange_rates(self) -> str:
        """Получить курс валют"""
        rates = await self.extras.get_exchange_rates()
        
        if rates.get('error'):
            return f"❌ Не удалось получить курс: {rates['error']}"
        
        return (
            f"💵 Курс валют:\n"
            f"USD: {rates['usd']['buy']:.2f} / {rates['usd']['sale']:.2f}\n"
            f"EUR: {rates['eur']['buy']:.2f} / {rates['eur']['sale']:.2f}\n"
            f"PLN: {rates['pln']['buy']:.2f} / {rates['pln']['sale']:.2f}"
        )
    
    async def _search_notes(self, user_id: int, args: Dict) -> str:
        """Найти заметки"""
        query = args.get('query', '')
        
        notes = await self.db.search_notes(user_id, query)
        
        if not notes:
            return f"❌ Заметок с '{query}' не найдено"
        
        result = f"📝 Найдено заметок: {len(notes)}\n\n"
        for note in notes[:5]:  # Первые 5
            result += f"#{note['id']}"
            if note['title']:
                result += f" {note['title']}"
            result += f"\n{note['content'][:100]}...\n\n"
        
        return result
    
    async def _recall_memory(self, user_id: int, args: Dict) -> str:
        """Получить память"""
        category = args.get('category', 'all')
        
        if category == 'all':
            category = None
        
        facts = await self.memory.recall_facts(user_id, category)
        
        if not facts:
            return "❌ В памяти пока ничего нет"
        
        result = "🧠 Что я помню:\n\n"
        current_cat = None
        
        for fact in facts:
            if fact['category'] != current_cat:
                current_cat = fact['category']
                cat_ru = {
                    'personal': 'Личное',
                    'work': 'Работа',
                    'preferences': 'Предпочтения',
                    'learning': 'Обучение'
                }.get(current_cat, current_cat)
                result += f"\n📁 {cat_ru}:\n"
            
            result += f"  • {fact['key']}: {fact['value']}\n"
        
        return result
    
    async def _get_work_stats(self, user_id: int, args: Dict) -> str:
        """Получить статистику работы"""
        date = args.get('date', None)
        team = args.get('team', 'Good Bunny')
        
        try:
            # Парсим отчеты
            reports = await self.parser.parse_reports(team=team, report_date=date)
            
            if not reports.get('success'):
                return f"❌ Ошибка парсинга: {reports.get('error', 'Неизвестная ошибка')}"
            
            # Формируем официальный отчет
            result = f"ОТЧЕТ ПО РАБОТЕ СОТРУДНИКОВ\n"
            result += f"Дата: {reports['date']}\n"
            result += f"Команда: {reports['team']}\n\n"
            result += f"Всего работников: {reports['workers_count']}\n"
            result += f"SFS (успешных): {reports['total_sfs']}\n"
            result += f"Only Now: {reports['total_only_now']}\n"
            result += f"SCH (проверено): {reports['total_sch']}\n"
            result += f"Работников с обнаруженными скам-ассистентами: {reports['scam_detected']}\n"
            
            # Детали по работникам, нашедшим скам-ассистентов
            workers_with_scam = [w for w in reports['workers'] if w.get('has_scam')]
            
            if workers_with_scam:
                result += f"\nРаботники, обнаружившие скам-ассистентов:\n"
                for w in workers_with_scam[:10]:
                    result += f"- {w['name']} (SFS: {w['sfs']}, SCH: {w['sch']})\n"
            
            return result
            
        except Exception as e:
            return f"❌ Ошибка получения статистики: {str(e)}"
    
    async def _check_worker_scam(self, user_id: int, args: Dict) -> str:
        """Проверить скам у конкретного работника"""
        worker_name = args.get('worker_name')
        date = args.get('date', None)
        team = args.get('team', 'Good Bunny')
        
        try:
            # Получаем скриншоты и детали скама
            result = await self.parser.get_worker_scam_screenshots(
                worker_name=worker_name,
                team=team,
                report_date=date
            )
            
            if not result.get('success'):
                return f"❌ {result.get('error', 'Ошибка проверки')}"
            
            worker = result['worker']
            message = result['message']
            
            # Формируем отчет
            output = f"👤 **{worker['name']}** (@{worker['username'] or 'N/A'})\n"
            output += f"📊 SFS: {worker['sfs']} | Only Now: {worker['only_now']} | SCH: {worker['sch']}\n\n"
            output += f"{message}\n"
            
            if worker.get('has_scam') and worker.get('scam_details'):
                details = worker['scam_details']
                if details.get('text'):
                    output += f"\n📋 **Детали скама:**\n{details['text'][:500]}...\n"
                
                if details.get('screenshot'):
                    output += f"\n📸 Скриншот сохранен: {details['screenshot']}"
            
            return output
            
        except Exception as e:
            return f"❌ Ошибка проверки работника: {str(e)}"

