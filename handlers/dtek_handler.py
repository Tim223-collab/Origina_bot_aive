"""
Обработчик команд для ДТЕК мониторинга
"""
from telegram import Update
from telegram.ext import ContextTypes
from services.dtek_monitor_service import DTEKMonitorService
import logging


logger = logging.getLogger(__name__)


class DTEKHandler:
    """
    Обработчик команд ДТЕК
    """
    
    def __init__(self, dtek_service: DTEKMonitorService):
        self.dtek = dtek_service
    
    async def setup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Настройка адреса для мониторинга
        
        Команда: /dtek_setup <город> <улица> <дом> [черга]
        """
        user = update.effective_user
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "🔌 **Настройка ДТЕК Мониторинга**\n\n"
                "Использование:\n"
                "`/dtek_setup <город> <улица> <дом> [черга]`\n\n"
                "Примеры:\n"
                "`/dtek_setup \"м. Дніпро\" \"вул. Калинова\" 47 1.2`\n"
                "`/dtek_setup Дніпро Калинова 47`\n\n"
                "**Черга** (опционально): 1.1, 1.2, 2.1, 2.2 и т.д.",
                parse_mode="Markdown"
            )
            return
        
        # Парсим аргументы
        city = context.args[0]
        street = context.args[1]
        building = context.args[2]
        queue = context.args[3] if len(context.args) > 3 else None
        
        # Добавляем префиксы если нужно
        if not city.startswith("м."):
            city = f"м. {city}"
        
        if not street.startswith("вул."):
            street = f"вул. {street}"
        
        # Сохраняем адрес
        self.dtek.set_user_address(user.id, city, street, building, queue)
        
        response = f"""✅ **Адрес сохранен!**

📍 **Город:** {city}
📍 **Улица:** {street}
📍 **Дом:** {building}
"""
        
        if queue:
            response += f"⚡ **Черга:** {queue}\n"
        
        response += "\n**Что дальше?**\n"
        response += "• `/dtek_now` - проверить сейчас\n"
        response += "• `/dtek_today` - график на сегодня\n"
        response += "• `/dtek_week` - график на неделю\n"
        response += "• `/dtek_monitor_start` - включить уведомления"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def check_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Проверяет текущий статус
        
        Команда: /dtek_now
        """
        user = update.effective_user
        
        # Проверяем настроен ли адрес
        if not self.dtek.get_user_address(user.id):
            await update.message.reply_text(
                "⚠️ Адрес не настроен.\n\n"
                "Используй `/dtek_setup` для настройки.",
                parse_mode="Markdown"
            )
            return
        
        await update.message.reply_text("🔍 Проверяю текущий статус...")
        
        try:
            result = await self.dtek.get_current_status(user.id)
            
            if not result.get("success"):
                await update.message.reply_text(
                    f"❌ Ошибка: {result.get('error')}"
                )
                return
            
            message = result.get("message", "")
            current_time = result.get("current_time", "")
            has_shutdown = result.get("has_shutdown_now", False)
            today_shutdowns = result.get("today_shutdowns", [])
            
            response = f"""🔌 **Статус Электроэнергии**

⏰ **Текущее время:** {current_time}

{message}
"""
            
            if today_shutdowns:
                response += f"\n📅 **График на сегодня:**\n"
                for time_slot in today_shutdowns:
                    icon = "⚡" if has_shutdown else "🕐"
                    response += f"{icon} {time_slot}\n"
            else:
                response += "\n✅ **Сегодня отключений не запланировано!**"
            
            await update.message.reply_text(response, parse_mode="Markdown")
        
        except Exception as e:
            logger.error(f"❌ Error in check_now: {e}")
            await update.message.reply_text("❌ Произошла ошибка при проверке статуса")
    
    async def today_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показывает график на сегодня
        
        Команда: /dtek_today
        """
        user = update.effective_user
        
        if not self.dtek.get_user_address(user.id):
            await update.message.reply_text(
                "⚠️ Адрес не настроен. Используй `/dtek_setup`",
                parse_mode="Markdown"
            )
            return
        
        await update.message.reply_text("📅 Получаю график на сегодня...")
        
        try:
            result = await self.dtek.get_today_schedule(user.id)
            
            if not result.get("success"):
                await update.message.reply_text(f"❌ Ошибка: {result.get('error')}")
                return
            
            schedule = result.get("schedule")
            warnings = result.get("warnings", [])
            
            response = "📅 **График Отключений на Сегодня**\n\n"
            
            # Предупреждения
            if warnings:
                for warning in warnings:
                    response += f"⚠️ {warning}\n\n"
            
            # График
            if schedule and schedule.get("has_shutdowns"):
                response += f"**Дата:** {schedule.get('date_text', '')}\n\n"
                response += "⚡ **Отключения:**\n"
                for time_slot in schedule.get("shutdown_times", []):
                    response += f"• {time_slot}\n"
            else:
                response += "✅ **Отключений не запланировано!**\n"
            
            response += "\n💡 Совет: Включи мониторинг `/dtek_monitor_start` для автоматических уведомлений"
            
            await update.message.reply_text(response, parse_mode="Markdown")
        
        except Exception as e:
            logger.error(f"❌ Error in today_schedule: {e}")
            await update.message.reply_text("❌ Произошла ошибка")
    
    async def week_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показывает график на неделю
        
        Команда: /dtek_week
        """
        user = update.effective_user
        
        if not self.dtek.get_user_address(user.id):
            await update.message.reply_text(
                "⚠️ Адрес не настроен. Используй `/dtek_setup`",
                parse_mode="Markdown"
            )
            return
        
        await update.message.reply_text("📅 Получаю график на неделю...")
        
        try:
            result = await self.dtek.get_week_schedule(user.id)
            
            if not result.get("success"):
                await update.message.reply_text(f"❌ Ошибка: {result.get('error')}")
                return
            
            schedule = result.get("schedule", [])
            warnings = result.get("warnings", [])
            address = result.get("address", {})
            
            response = "📅 **График Отключений на Неделю**\n\n"
            response += f"📍 **Адрес:** {address.get('street')}, {address.get('building')}\n"
            
            if address.get('queue'):
                response += f"⚡ **Черга:** {address.get('queue')}\n"
            
            response += "\n"
            
            # Предупреждения
            if warnings:
                for warning in warnings[:2]:  # Максимум 2 предупреждения
                    response += f"⚠️ {warning[:100]}...\n\n"
            
            # График по дням
            for day in schedule:
                date_text = day.get("date_text", "")
                has_shutdowns = day.get("has_shutdowns", False)
                shutdown_times = day.get("shutdown_times", [])
                
                if has_shutdowns:
                    response += f"**{date_text}**\n"
                    # Показываем максимум 3 первых слота
                    for time_slot in shutdown_times[:3]:
                        response += f"⚡ {time_slot}\n"
                    if len(shutdown_times) > 3:
                        response += f"   ...и еще {len(shutdown_times) - 3}\n"
                    response += "\n"
                else:
                    response += f"**{date_text}** ✅\n\n"
            
            await update.message.reply_text(response, parse_mode="Markdown")
        
        except Exception as e:
            logger.error(f"❌ Error in week_schedule: {e}")
            await update.message.reply_text("❌ Произошла ошибка")
    
    async def start_monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Запускает мониторинг
        
        Команда: /dtek_monitor_start
        """
        user = update.effective_user
        
        if not self.dtek.get_user_address(user.id):
            await update.message.reply_text(
                "⚠️ Адрес не настроен. Используй `/dtek_setup`",
                parse_mode="Markdown"
            )
            return
        
        # Запускаем мониторинг (проверка каждые 30 минут)
        bot = context.bot
        await self.dtek.start_monitoring(user.id, bot, check_interval=1800)
        
        response = """✅ **Мониторинг Запущен!**

🔔 **Я буду уведомлять тебя о:**
• Изменениях в графике отключений
• Приближающихся отключениях (за 15-30 минут)
• Внезапных изменениях

⏰ **Проверка:** каждые 30 минут

**Команды:**
• `/dtek_now` - проверить сейчас
• `/dtek_monitor_stop` - остановить мониторинг
• `/dtek_monitor_status` - статус"""
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def stop_monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Останавливает мониторинг
        
        Команда: /dtek_monitor_stop
        """
        user = update.effective_user
        
        await self.dtek.stop_monitoring(user.id)
        
        await update.message.reply_text(
            "⏸️ **Мониторинг остановлен.**\n\n"
            "Запустить снова: `/dtek_monitor_start`",
            parse_mode="Markdown"
        )
    
    async def monitor_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показывает статус мониторинга
        
        Команда: /dtek_monitor_status
        """
        user = update.effective_user
        
        is_monitoring = user.id in self.dtek.monitoring_tasks
        address = self.dtek.get_user_address(user.id)
        
        response = "📊 **Статус ДТЕК Мониторинга**\n\n"
        
        if address:
            response += f"📍 **Адрес:** {address.get('street')}, {address.get('building')}\n"
            if address.get('queue'):
                response += f"⚡ **Черга:** {address.get('queue')}\n"
        else:
            response += "⚠️ **Адрес не настроен**\n"
        
        response += "\n"
        
        if is_monitoring:
            response += "🟢 **Мониторинг:** Активен\n"
            response += "⏰ **Проверка:** каждые 30 минут\n"
        else:
            response += "⚪ **Мониторинг:** Не активен\n"
        
        response += "\n**Команды:**\n"
        if address:
            response += "• `/dtek_now` - проверить сейчас\n"
            response += "• `/dtek_today` - график на сегодня\n"
            
            if not is_monitoring:
                response += "• `/dtek_monitor_start` - запустить\n"
            else:
                response += "• `/dtek_monitor_stop` - остановить\n"
        else:
            response += "• `/dtek_setup` - настроить адрес\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")

