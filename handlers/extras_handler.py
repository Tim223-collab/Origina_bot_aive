"""
Обработчики дополнительных функций
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from services.extras_service import ExtrasService


class ExtrasHandler:
    def __init__(self, extras: ExtrasService):
        self.extras = extras
    
    # === ИНФОРМАЦИЯ ===
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /weather [город] - показывает погоду
        """
        city = " ".join(context.args) if context.args else "Moscow"
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        weather = await self.extras.get_weather(city)
        
        if weather:
            await update.message.reply_text(f"🌤 {weather}")
        else:
            await update.message.reply_text("❌ Не удалось получить погоду.")
    
    async def rates_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /rates - показывает курсы валют
        """
        await update.message.chat.send_action(ChatAction.TYPING)
        
        rates = await self.extras.get_exchange_rates()
        
        if rates:
            message = f"""💰 **Курсы валют ЦБ РФ**

💵 USD: {rates['USD']:.2f} ₽
💶 EUR: {rates['EUR']:.2f} ₽
💴 CNY: {rates['CNY']:.2f} ₽

📅 {rates['date'][:10]}
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Не удалось получить курсы.")
    
    async def crypto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /crypto [символ] - показывает цену криптовалюты
        """
        symbol = context.args[0].upper() if context.args else "BTC"
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        price = await self.extras.get_crypto_price(symbol)
        
        if price:
            await update.message.reply_text(
                f"₿ **{price['symbol']}**: ${price['price']} {price['currency']}"
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось получить цену для {symbol}"
            )
    
    # === РАЗВЛЕЧЕНИЯ ===
    
    async def fact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /fact - интересный факт
        """
        fact = self.extras.get_random_fact()
        await update.message.reply_text(fact)
    
    async def joke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /joke - случайная шутка
        """
        joke = self.extras.get_joke()
        await update.message.reply_text(joke)
    
    async def quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /quote - мотивационная цитата
        """
        quote = self.extras.get_motivational_quote()
        await update.message.reply_text(quote)
    
    async def activity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /activity - предлагает случайную активность
        """
        await update.message.chat.send_action(ChatAction.TYPING)
        
        activity = await self.extras.get_random_activity()
        
        if activity:
            await update.message.reply_text(activity)
        else:
            await update.message.reply_text("🤔 Попробуй сходить прогуляться!")
    
    async def tips_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /tips [категория] - полезные советы
        Категории: productivity, health, coding
        """
        category = context.args[0] if context.args else "productivity"
        
        if category not in ["productivity", "health", "coding"]:
            await update.message.reply_text(
                "📚 Доступные категории:\n"
                "• productivity\n"
                "• health\n"
                "• coding"
            )
            return
        
        tip = self.extras.get_tips(category)
        await update.message.reply_text(tip)
    
    # === ИГРЫ ===
    
    async def dice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /dice [количество]d[граней] - бросает кости
        Пример: /dice 2d6 или /dice 3d20
        """
        sides = 6
        count = 1
        
        if context.args:
            try:
                arg = context.args[0].lower()
                if 'd' in arg:
                    parts = arg.split('d')
                    count = int(parts[0]) if parts[0] else 1
                    sides = int(parts[1]) if parts[1] else 6
                else:
                    count = int(arg)
            except:
                pass
        
        result = self.extras.roll_dice(sides, count)
        
        dice_emoji = "🎲"
        rolls_text = " + ".join(str(r) for r in result['rolls'])
        
        message = f"{dice_emoji} **Бросок {result['count']}d{result['sides']}**\n\n"
        message += f"Результаты: {rolls_text}\n"
        message += f"**Сумма: {result['total']}**"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def ball8_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /8ball <вопрос> - магический шар 8
        """
        question = " ".join(context.args) if context.args else None
        
        if not question:
            await update.message.reply_text(
                "🔮 **Магический шар 8**\n\n"
                "Задай вопрос, на который можно ответить да/нет:\n"
                "`/8ball Стоит ли мне учить Python?`"
            )
            return
        
        answer = self.extras.magic_8ball(question)
        await update.message.reply_text(answer)
    
    async def choose_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /choose <вариант1> или <вариант2> ... - выбирает случайный вариант
        """
        if not context.args:
            await update.message.reply_text(
                "🎯 **Помощник выбора**\n\n"
                "Использование:\n"
                "`/choose пицца или суши или бургер`"
            )
            return
        
        text = " ".join(context.args)
        choices = [c.strip() for c in text.split("или")]
        
        if len(choices) < 2:
            await update.message.reply_text(
                "❓ Нужно минимум 2 варианта, разделенных словом 'или'"
            )
            return
        
        import random
        choice = random.choice(choices)
        
        await update.message.reply_text(
            f"🎯 Мой выбор: **{choice}**",
            parse_mode='Markdown'
        )

