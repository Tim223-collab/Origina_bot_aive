"""
Обработчик эмоционального интеллекта
"""
from telegram import Update
from telegram.ext import ContextTypes
from services.emotional_intelligence import EmotionalIntelligence


class EmotionHandler:
    """
    Обработчик команд для работы с эмоциональным интеллектом
    """
    
    def __init__(self, emotional: EmotionalIntelligence):
        self.emotional = emotional
    
    async def emotion_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показывает эмоциональную статистику пользователя
        
        Команда: /emotion
        """
        user = update.effective_user
        
        # Получаем сводку за 24 часа
        summary_24h = self.emotional.get_emotion_summary(user.id, hours=24)
        
        # Получаем сводку за последние 6 часов
        summary_6h = self.emotional.get_emotion_summary(user.id, hours=6)
        
        # Формируем ответ
        if summary_24h["count"] == 0:
            await update.message.reply_text(
                "📊 Пока нет данных для анализа эмоций.\n"
                "Продолжай общаться со мной, и я научусь лучше понимать тебя! 💙"
            )
            return
        
        # Эмодзи для эмоций
        emotion_emojis = {
            "happy": "😊",
            "sad": "😔",
            "anxious": "😰",
            "angry": "😠",
            "tired": "😴",
            "excited": "🤩",
            "confused": "😕",
            "neutral": "😐"
        }
        
        # Названия эмоций на русском
        emotion_names = {
            "happy": "Радость",
            "sad": "Грусть",
            "anxious": "Тревога",
            "angry": "Злость",
            "tired": "Усталость",
            "excited": "Восторг",
            "confused": "Растерянность",
            "neutral": "Нейтрально"
        }
        
        # Описание тренда
        trend_text = {
            "improving": "📈 Улучшается",
            "worsening": "📉 Ухудшается",
            "stable": "➡️ Стабильно"
        }
        
        # Формируем распределение эмоций за 24 часа
        emotions_list_24h = []
        for emotion, percentage in sorted(
            summary_24h["emotions_distribution"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            emoji = emotion_emojis.get(emotion, "")
            name = emotion_names.get(emotion, emotion)
            bar_length = int(percentage * 10)
            bar = "█" * bar_length + "░" * (10 - bar_length)
            emotions_list_24h.append(
                f"{emoji} {name}: {bar} {percentage*100:.0f}%"
            )
        
        # Формируем распределение эмоций за 6 часов
        emotions_list_6h = []
        if summary_6h["count"] > 0:
            for emotion, percentage in sorted(
                summary_6h["emotions_distribution"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                emoji = emotion_emojis.get(emotion, "")
                name = emotion_names.get(emotion, emotion)
                bar_length = int(percentage * 10)
                bar = "█" * bar_length + "░" * (10 - bar_length)
                emotions_list_6h.append(
                    f"{emoji} {name}: {bar} {percentage*100:.0f}%"
                )
        
        # Доминирующая эмоция
        dominant_24h = summary_24h["dominant_emotion"]
        dominant_emoji_24h = emotion_emojis.get(dominant_24h, "")
        dominant_name_24h = emotion_names.get(dominant_24h, dominant_24h)
        
        response = f"""💙 **Эмоциональная Аналитика AIVE**

📅 **За последние 24 часа:**
Доминирующая эмоция: {dominant_emoji_24h} {dominant_name_24h}
Средняя интенсивность: {summary_24h['average_intensity']*100:.0f}%
Тренд: {trend_text.get(summary_24h['trend'], summary_24h['trend'])}
Сообщений проанализировано: {summary_24h['count']}

**Распределение эмоций (24ч):**
{chr(10).join(emotions_list_24h)}
"""
        
        if summary_6h["count"] > 0:
            dominant_6h = summary_6h["dominant_emotion"]
            dominant_emoji_6h = emotion_emojis.get(dominant_6h, "")
            dominant_name_6h = emotion_names.get(dominant_6h, dominant_6h)
            
            response += f"""
⏰ **За последние 6 часов:**
Доминирующая эмоция: {dominant_emoji_6h} {dominant_name_6h}
Средняя интенсивность: {summary_6h['average_intensity']*100:.0f}%

**Распределение эмоций (6ч):**
{chr(10).join(emotions_list_6h)}
"""
        
        # Проверяем нужно ли поддержать
        support_msg = self.emotional.get_support_message(user.id)
        if support_msg:
            response += f"\n\n{support_msg}"
        
        # Проверяем нужно ли поздравить
        celebration_msg = self.emotional.get_celebration_message(user.id)
        if celebration_msg:
            response += f"\n\n{celebration_msg}"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def test_emotion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Анализирует эмоцию в сообщении
        
        Команда: /test_emotion <текст>
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "Использование: /test_emotion <текст для анализа>\n\n"
                "Пример: /test_emotion Я сегодня очень устал и раздражен"
            )
            return
        
        text = " ".join(context.args)
        
        # Анализируем эмоцию
        analysis = self.emotional.analyze_emotion(text)
        
        # Эмодзи для эмоций
        emotion_emojis = {
            "happy": "😊",
            "sad": "😔",
            "anxious": "😰",
            "angry": "😠",
            "tired": "😴",
            "excited": "🤩",
            "confused": "😕",
            "neutral": "😐"
        }
        
        # Названия эмоций
        emotion_names = {
            "happy": "Радость",
            "sad": "Грусть",
            "anxious": "Тревога",
            "angry": "Злость",
            "tired": "Усталость",
            "excited": "Восторг",
            "confused": "Растерянность",
            "neutral": "Нейтрально"
        }
        
        emotion = analysis["emotion"]
        emoji = emotion_emojis.get(emotion, "")
        name = emotion_names.get(emotion, emotion)
        
        response = f"""🎭 **Анализ Эмоции**

Текст: _{text}_

{emoji} **Эмоция:** {name}
💪 **Интенсивность:** {analysis['intensity']*100:.0f}%
🎯 **Уверенность:** {analysis['confidence']*100:.0f}%
📝 **Ключевые слова:** {', '.join(analysis['keywords_found']) if analysis['keywords_found'] else 'не найдены'}
🗣️ **Рекомендуемый тон ответа:** {analysis['tone']}
"""
        
        await update.message.reply_text(response, parse_mode="Markdown")

