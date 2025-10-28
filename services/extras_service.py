"""
Дополнительные сервисы: погода, курсы валют, развлечения
"""
import aiohttp
from typing import Dict, Optional
import random


class ExtrasService:
    """Дополнительные полезные функции"""
    
    def __init__(self):
        pass
    
    async def get_weather(self, city: str = "Moscow") -> Optional[str]:
        """
        Получает погоду для города (через wttr.in)
        """
        try:
            url = f"https://wttr.in/{city}?format=3&lang=ru"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        weather = await response.text()
                        return weather.strip()
            return None
        except Exception as e:
            print(f"❌ Ошибка получения погоды: {e}")
            return None
    
    async def get_exchange_rates(self, base: str = "USD") -> Optional[Dict]:
        """
        Получает курсы валют
        """
        try:
            # Используем публичное API ЦБ РФ
            url = "https://www.cbr-xml-daily.ru/daily_json.js"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "USD": data["Valute"]["USD"]["Value"],
                            "EUR": data["Valute"]["EUR"]["Value"],
                            "CNY": data["Valute"]["CNY"]["Value"],
                            "date": data["Date"]
                        }
            return None
        except Exception as e:
            print(f"❌ Ошибка получения курсов: {e}")
            return None
    
    async def get_crypto_price(self, symbol: str = "BTC") -> Optional[Dict]:
        """
        Получает цену криптовалюты
        """
        try:
            url = f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "symbol": symbol,
                            "price": data["data"]["amount"],
                            "currency": data["data"]["currency"]
                        }
            return None
        except Exception as e:
            print(f"❌ Ошибка получения цены крипты: {e}")
            return None
    
    def get_random_fact(self) -> str:
        """
        Возвращает случайный интересный факт
        """
        facts = [
            "🧠 Человеческий мозг генерирует около 70,000 мыслей в день.",
            "🌍 Россия занимает более 11% всей суши на Земле.",
            "⚡ Молния в 5 раз горячее поверхности Солнца.",
            "🐙 У осьминога три сердца и голубая кровь.",
            "🌙 На Луне нет атмосферы, поэтому там абсолютная тишина.",
            "🔋 Батарейки изобрели на 40 лет раньше, чем нашли им применение.",
            "🎮 В Японии больше животных в качестве домашних питомцев, чем детей.",
            "🌊 95% мирового океана остаются неизученными.",
            "☕ Кофе - второй по объему торговли товар в мире после нефти.",
            "🐝 Пчелы умеют считать до четырех.",
            "🧬 ДНК человека на 50% совпадает с ДНК банана.",
            "🚀 В космосе металлические поверхности могут самопроизвольно свариваться.",
            "🎵 Музыка может изменять сердечный ритм и кровяное давление.",
            "🐌 Улитка может спать три года подряд.",
            "💎 Алмазы можно сделать из арахисового масла."
        ]
        return random.choice(facts)
    
    def get_joke(self) -> str:
        """
        Возвращает случайную шутку
        """
        jokes = [
            "Программист моет голову шампунем.\nИнструкция: нанести, намылить, смыть, повторить.\nПрограммист все еще в душе...",
            "- Сколько программистов нужно, чтобы вкрутить лампочку?\n- Ни одного, это аппаратная проблема.",
            "Девушка спрашивает программиста:\n- Милый, сходи в магазин за хлебом.\n- Хорошо, дорогая.\nПрограммист ушел и не вернулся. Она забыла указать return.",
            "Почему программисты путают Хэллоуин и Рождество?\nПотому что OCT 31 = DEC 25 😄",
            "- Кто такой full-stack разработчик?\n- Это человек, который умеет создавать баги и в фронтенде, и в бэкенде.",
            "Жена программисту:\n- Дорогой, купи батон хлеба, а если будут яйца - возьми десяток.\nОн пришел с 10 батонами:\n- Яйца были!",
            "Два программиста говорят:\n- У меня bug.\n- А у меня feature!",
            "- Как программисты называют свои ошибки?\n- Недокументированными фичами! 🐛",
        ]
        return random.choice(jokes)
    
    def get_motivational_quote(self) -> str:
        """
        Возвращает мотивационную цитату
        """
        quotes = [
            "💪 \"Единственный способ сделать великую работу - любить то, что делаешь.\" - Стив Джобс",
            "🎯 \"Не бойтесь начать с малого. Великие дела начинаются с малых шагов.\"",
            "🚀 \"Будущее принадлежит тем, кто верит в красоту своих мечтаний.\" - Элеонора Рузвельт",
            "⚡ \"Успех - это способность идти от неудачи к неудаче, не теряя энтузиазма.\" - Черчилль",
            "🌟 \"Лучшее время посадить дерево было 20 лет назад. Второе лучшее время - сегодня.\"",
            "💡 \"Невозможно - это всего лишь громкое слово, за которым прячутся маленькие люди.\"",
            "🎨 \"Креативность - это интеллект, который развлекается.\" - Альберт Эйнштейн",
            "🏆 \"Победа начинается с начала. Начни прямо сейчас.\"",
        ]
        return random.choice(quotes)
    
    async def get_random_activity(self) -> Optional[str]:
        """
        Предлагает случайную активность (через Bored API)
        """
        try:
            url = "https://www.boredapi.com/api/activity"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        activity = data["activity"]
                        activity_type = data["type"]
                        return f"💡 Предложение: {activity}\n📁 Категория: {activity_type}"
            return None
        except Exception as e:
            print(f"❌ Ошибка получения активности: {e}")
            return None
    
    def get_tips(self, category: str = "productivity") -> str:
        """
        Возвращает советы по разным категориям
        """
        tips = {
            "productivity": [
                "⏰ Используй технику Помодоро: 25 минут работы, 5 минут отдых.",
                "📝 Записывай все задачи, освобождай мозг для творчества.",
                "🎯 Начинай день с самой важной задачи (Eat the Frog).",
                "🚫 Выключай уведомления на время глубокой работы.",
                "☕ Делай регулярные перерывы каждые 90 минут.",
            ],
            "health": [
                "💧 Пей не менее 2 литров воды в день.",
                "🚶 Делай перерывы на прогулку каждые 2 часа.",
                "👀 Правило 20-20-20: каждые 20 минут смотри на объект в 20 футах на 20 секунд.",
                "🧘 Медитируй 10 минут в день для снижения стресса.",
                "😴 Спи не менее 7-8 часов для восстановления.",
            ],
            "coding": [
                "📚 Читай чужой код - лучший способ учиться.",
                "🧪 Пиши тесты - они экономят время в долгосрочной перспективе.",
                "🔍 Code review - спрашивай мнение коллег о своем коде.",
                "📖 Документируй код для будущего себя.",
                "♻️ Рефактори регулярно, не копи технический долг.",
            ]
        }
        
        category_tips = tips.get(category, tips["productivity"])
        return random.choice(category_tips)
    
    def roll_dice(self, sides: int = 6, count: int = 1) -> Dict:
        """
        Бросает кости
        """
        if sides < 2 or sides > 100:
            sides = 6
        if count < 1 or count > 10:
            count = 1
        
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        
        return {
            "rolls": rolls,
            "total": total,
            "count": count,
            "sides": sides
        }
    
    def magic_8ball(self, question: str = None) -> str:
        """
        Магический шар 8 - предсказатель
        """
        responses = [
            "🔮 Да, определенно!",
            "🔮 Без сомнений.",
            "🔮 Можешь быть уверен.",
            "🔮 Да.",
            "🔮 Скорее всего да.",
            "🔮 Пока неясно, спроси позже.",
            "🔮 Сконцентрируйся и спроси снова.",
            "🔮 Лучше не говорить сейчас.",
            "🔮 Не могу предсказать.",
            "🔮 Мой ответ - нет.",
            "🔮 Мои источники говорят - нет.",
            "🔮 Очень сомнительно.",
        ]
        
        response = random.choice(responses)
        
        if question:
            return f"❓ {question}\n{response}"
        else:
            return response

