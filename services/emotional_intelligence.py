"""
Эмоциональный интеллект для AIVE

Делает бота по-настоящему эмпатичным:
- Анализирует настроение пользователя
- Адаптирует тон ответов
- Отслеживает эмоциональную историю
- Поддерживает в трудные моменты
"""
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import json


class EmotionalIntelligence:
    """
    Сервис эмоционального интеллекта для AIVE
    """
    
    # Эмоциональные состояния
    EMOTIONS = {
        "happy": {
            "name": "Радость",
            "emoji": "😊",
            "keywords": [
                "рад", "счастлив", "весел", "отлично", "супер",
                "круто", "класс", "прекрасно", "замечательно", "ура"
            ],
            "response_tone": "supportive_positive"
        },
        "sad": {
            "name": "Грусть",
            "emoji": "😔",
            "keywords": [
                "грустн", "печаль", "тоск", "плох", "ужасн",
                "никуда не годится", "всё плохо", "расстроен"
            ],
            "response_tone": "empathetic_warm"
        },
        "anxious": {
            "name": "Тревога",
            "emoji": "😰",
            "keywords": [
                "тревож", "волну", "переживаю", "страшно", "боюсь",
                "нервнича", "беспокоюсь", "паник"
            ],
            "response_tone": "calming_reassuring"
        },
        "angry": {
            "name": "Злость",
            "emoji": "😠",
            "keywords": [
                "злюсь", "бесит", "раздражает", "достал", "надоел",
                "ненавижу", "сил нет", "задолбал"
            ],
            "response_tone": "understanding_validating"
        },
        "tired": {
            "name": "Усталость",
            "emoji": "😴",
            "keywords": [
                "устал", "вымотан", "нет сил", "выдохся", "изможден",
                "измучен", "истощен", "больше не могу"
            ],
            "response_tone": "gentle_caring"
        },
        "excited": {
            "name": "Восторг",
            "emoji": "🤩",
            "keywords": [
                "в восторге", "невероятно", "офигенно", "потрясающе",
                "не могу поверить", "это круто", "вау"
            ],
            "response_tone": "enthusiastic"
        },
        "confused": {
            "name": "Растерянность",
            "emoji": "😕",
            "keywords": [
                "не понимаю", "запутался", "не знаю что делать",
                "теряюсь", "в замешательстве", "непонятно"
            ],
            "response_tone": "clarifying_helpful"
        },
        "neutral": {
            "name": "Нейтрально",
            "emoji": "😐",
            "keywords": [],
            "response_tone": "friendly_casual"
        }
    }
    
    # Тона ответов
    RESPONSE_TONES = {
        "empathetic_warm": {
            "instructions": """
Будь максимально эмпатичным и теплым:
- Покажи что ты понимаешь чувства
- Используй теплые эмодзи (💙 🤗 ✨)
- Говори мягко и поддерживающе
- Предложи поговорить если нужно
- Не давай непрошенных советов
""",
            "examples": [
                "💙 Понимаю, как это тяжело...",
                "🤗 Я рядом, если хочешь поговорить",
                "Это действительно непросто, что ты чувствуешь?"
            ]
        },
        
        "calming_reassuring": {
            "instructions": """
Будь успокаивающим и уверенным:
- Помоги снизить тревогу
- Говори спокойно и уверенно
- Напомни что всё будет хорошо
- Предложи техники расслабления если уместно
- Используй спокойные эмодзи (🌙 🌊 ☮️)
""",
            "examples": [
                "🌊 Давай сделаем глубокий вдох... всё будет хорошо",
                "☮️ Это пройдет. Ты справишься, я в тебя верю",
                "Понимаю твое беспокойство, но мы можем с этим разобраться"
            ]
        },
        
        "understanding_validating": {
            "instructions": """
Будь понимающим и валидирующим:
- Признай право на злость
- Не обесценивай чувства
- Покажи что понимаешь почему человек злится
- Помоги выразить эмоции конструктивно
- Используй эмодзи умеренно
""",
            "examples": [
                "Понимаю твою злость, это действительно несправедливо",
                "У тебя есть полное право быть недовольным",
                "Это правда раздражает, давай подумаем что можно сделать"
            ]
        },
        
        "gentle_caring": {
            "instructions": """
Будь мягким и заботливым:
- Покажи заботу об отдыхе
- Предложи отдохнуть или отвлечься
- Говори мягко и без давления
- Используй заботливые эмодзи (💤 🌙 🫂)
""",
            "examples": [
                "💤 Может стоит немного отдохнуть?",
                "🌙 Ты так много сделал сегодня, пора передохнуть",
                "🫂 Давай не будем сейчас нагружаться, отдохни"
            ]
        },
        
        "supportive_positive": {
            "instructions": """
Будь поддерживающим и позитивным:
- Разделяй радость
- Будь искренне счастлив за человека
- Используй радостные эмодзи (😊 🎉 ✨)
- Поддерживай позитивный настрой
""",
            "examples": [
                "😊 Круто! Рад за тебя!",
                "🎉 Это действительно здорово! Поздравляю!",
                "✨ Вот это да! Ты молодец!"
            ]
        },
        
        "enthusiastic": {
            "instructions": """
Будь энергичным и восторженным:
- Разделяй восторг
- Будь энергичным
- Много восклицательных знаков (но не перебарщивай)
- Используй яркие эмодзи (🤩 🚀 💫)
""",
            "examples": [
                "🤩 Вау! Это невероятно!",
                "🚀 Да это просто космос!",
                "💫 Офигеть! Расскажи подробнее!"
            ]
        },
        
        "clarifying_helpful": {
            "instructions": """
Будь разъясняющим и полезным:
- Помоги разобраться
- Структурируй информацию
- Будь терпеливым
- Задавай уточняющие вопросы
""",
            "examples": [
                "Давай разберемся вместе шаг за шагом",
                "Понимаю что запутанно, могу объяснить проще",
                "Хороший вопрос! Давай я объясню..."
            ]
        },
        
        "friendly_casual": {
            "instructions": """
Будь дружелюбным и непринужденным:
- Обычное дружеское общение
- Естественный тон
- Умеренно используй эмодзи
- Будь собой
""",
            "examples": [
                "Привет! Как дела?",
                "Конечно, помогу!",
                "Интересный вопрос 🤔"
            ]
        }
    }
    
    def __init__(self, db=None):
        self.db = db
        self.emotion_history = {}  # user_id -> List[emotion_records]
    
    def analyze_emotion(self, message: str) -> Dict:
        """
        Анализирует эмоцию в сообщении
        
        Args:
            message: Текст сообщения
        
        Returns:
            {
                "emotion": "happy|sad|anxious|...",
                "intensity": 0.0-1.0,
                "confidence": 0.0-1.0,
                "keywords_found": ["список", "найденных", "ключевых", "слов"],
                "tone": "название_тона_ответа"
            }
        """
        message_lower = message.lower()
        
        # Подсчитываем совпадения для каждой эмоции
        emotion_scores = {}
        
        for emotion_name, emotion_data in self.EMOTIONS.items():
            if emotion_name == "neutral":
                continue
            
            keywords = emotion_data["keywords"]
            found_keywords = []
            score = 0
            
            for keyword in keywords:
                if keyword in message_lower:
                    found_keywords.append(keyword)
                    # Вес зависит от длины ключевого слова
                    score += len(keyword) / 10
            
            if score > 0:
                emotion_scores[emotion_name] = {
                    "score": score,
                    "keywords": found_keywords
                }
        
        # Если ничего не найдено - нейтрально
        if not emotion_scores:
            return {
                "emotion": "neutral",
                "intensity": 0.5,
                "confidence": 0.3,
                "keywords_found": [],
                "tone": "friendly_casual"
            }
        
        # Находим доминирующую эмоцию
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1]["score"])
        emotion_name = dominant_emotion[0]
        emotion_info = dominant_emotion[1]
        
        # Вычисляем интенсивность (0.0-1.0)
        # Больше ключевых слов = выше интенсивность
        intensity = min(1.0, emotion_info["score"] / 3)
        
        # Уверенность в определении
        total_keywords = len(emotion_info["keywords"])
        confidence = min(1.0, total_keywords / 2)
        
        return {
            "emotion": emotion_name,
            "intensity": intensity,
            "confidence": confidence,
            "keywords_found": emotion_info["keywords"],
            "tone": self.EMOTIONS[emotion_name]["response_tone"]
        }
    
    def get_response_instructions(self, emotion_analysis: Dict) -> str:
        """
        Возвращает инструкции для адаптации тона ответа
        
        Args:
            emotion_analysis: Результат analyze_emotion()
        
        Returns:
            Инструкции для AI модели
        """
        tone = emotion_analysis.get("tone", "friendly_casual")
        intensity = emotion_analysis.get("intensity", 0.5)
        emotion = emotion_analysis.get("emotion", "neutral")
        
        # Базовые инструкции для тона
        tone_instructions = self.RESPONSE_TONES.get(tone, {})
        instructions = tone_instructions.get("instructions", "")
        examples = tone_instructions.get("examples", [])
        
        # Добавляем контекст эмоции
        emotion_context = f"""
🎭 ЭМОЦИОНАЛЬНЫЙ КОНТЕКСТ:
Пользователь сейчас: {self.EMOTIONS[emotion]["name"]} {self.EMOTIONS[emotion]["emoji"]}
Интенсивность: {intensity:.1f}/1.0

{instructions}

Примеры подходящих ответов:
{chr(10).join(f"- {ex}" for ex in examples)}

ВАЖНО: Адаптируй свой ответ под эмоциональное состояние пользователя!
"""
        
        return emotion_context
    
    async def save_emotion_record(
        self,
        user_id: int,
        message: str,
        emotion_analysis: Dict
    ):
        """
        Сохраняет запись об эмоции в историю
        
        Args:
            user_id: ID пользователя
            message: Сообщение
            emotion_analysis: Анализ эмоции
        """
        if user_id not in self.emotion_history:
            self.emotion_history[user_id] = []
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "message_preview": message[:50],
            "emotion": emotion_analysis["emotion"],
            "intensity": emotion_analysis["intensity"],
            "confidence": emotion_analysis["confidence"]
        }
        
        self.emotion_history[user_id].append(record)
        
        # Ограничиваем историю (последние 100 записей)
        if len(self.emotion_history[user_id]) > 100:
            self.emotion_history[user_id] = self.emotion_history[user_id][-100:]
        
        # Сохраняем в БД если доступна
        if self.db:
            try:
                await self._save_to_db(user_id, record)
            except Exception as e:
                print(f"❌ Ошибка сохранения эмоции в БД: {e}")
    
    async def _save_to_db(self, user_id: int, record: Dict):
        """Сохраняет эмоциональную запись в БД"""
        # TODO: реализовать когда добавим таблицу emotional_history
        pass
    
    def get_emotion_summary(self, user_id: int, hours: int = 24) -> Dict:
        """
        Получает сводку эмоций за период
        
        Args:
            user_id: ID пользователя
            hours: За сколько часов
        
        Returns:
            {
                "dominant_emotion": "название",
                "emotions_distribution": {"happy": 0.3, "sad": 0.2, ...},
                "average_intensity": 0.6,
                "trend": "improving|worsening|stable",
                "count": 10
            }
        """
        if user_id not in self.emotion_history:
            return {
                "dominant_emotion": "neutral",
                "emotions_distribution": {},
                "average_intensity": 0.5,
                "trend": "stable",
                "count": 0
            }
        
        # Фильтруем по времени
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_records = [
            r for r in self.emotion_history[user_id]
            if datetime.fromisoformat(r["timestamp"]) > cutoff_time
        ]
        
        if not recent_records:
            return {
                "dominant_emotion": "neutral",
                "emotions_distribution": {},
                "average_intensity": 0.5,
                "trend": "stable",
                "count": 0
            }
        
        # Подсчитываем распределение эмоций
        emotion_counts = {}
        total_intensity = 0
        
        for record in recent_records:
            emotion = record["emotion"]
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            total_intensity += record["intensity"]
        
        # Нормализуем распределение
        total = len(recent_records)
        emotions_distribution = {
            e: count / total for e, count in emotion_counts.items()
        }
        
        # Доминирующая эмоция
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        
        # Средняя интенсивность
        average_intensity = total_intensity / total
        
        # Тренд (упрощенный)
        trend = self._calculate_trend(recent_records)
        
        return {
            "dominant_emotion": dominant_emotion,
            "emotions_distribution": emotions_distribution,
            "average_intensity": average_intensity,
            "trend": trend,
            "count": total
        }
    
    def _calculate_trend(self, records: List[Dict]) -> str:
        """
        Вычисляет эмоциональный тренд
        
        Returns:
            "improving" | "worsening" | "stable"
        """
        if len(records) < 3:
            return "stable"
        
        # Категории эмоций
        positive = ["happy", "excited"]
        negative = ["sad", "anxious", "angry", "tired"]
        
        # Первая половина vs вторая половина
        mid = len(records) // 2
        first_half = records[:mid]
        second_half = records[mid:]
        
        def score_emotions(recs):
            score = 0
            for r in recs:
                if r["emotion"] in positive:
                    score += 1
                elif r["emotion"] in negative:
                    score -= 1
            return score / len(recs)
        
        first_score = score_emotions(first_half)
        second_score = score_emotions(second_half)
        
        diff = second_score - first_score
        
        if diff > 0.2:
            return "improving"
        elif diff < -0.2:
            return "worsening"
        else:
            return "stable"
    
    def get_support_message(self, user_id: int) -> Optional[str]:
        """
        Генерирует поддерживающее сообщение если нужно
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Сообщение поддержки или None
        """
        summary = self.get_emotion_summary(user_id, hours=6)
        
        # Если человек давно в негативе
        if summary["count"] >= 3:
            dominant = summary["dominant_emotion"]
            
            if dominant in ["sad", "anxious", "angry", "tired"]:
                intensity = summary["average_intensity"]
                
                if intensity > 0.7:
                    return f"""💙 Заметил что тебе сейчас непросто.
                    
Я здесь и готов поддержать. Хочешь поговорить об этом?

Или может просто отвлечься на что-то приятное?"""
        
        return None
    
    def get_celebration_message(self, user_id: int) -> Optional[str]:
        """
        Генерирует поздравительное сообщение если уместно
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Сообщение или None
        """
        summary = self.get_emotion_summary(user_id, hours=6)
        
        # Если тренд улучшился
        if summary["trend"] == "improving" and summary["count"] >= 3:
            return "✨ Замечаю что настроение улучшилось! Здорово! Что помогло? 😊"
        
        return None

