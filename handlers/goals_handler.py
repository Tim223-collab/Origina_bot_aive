"""
Обработчик команд для работы с целями
"""
from telegram import Update
from telegram.ext import ContextTypes
from services.goals_service import GoalsService
from datetime import datetime, timedelta
import pytz


class GoalsHandler:
    """
    Обработчик команд целей и трекинга
    """
    
    def __init__(self, goals: GoalsService):
        self.goals = goals
    
    async def create_goal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Создает новую цель
        
        Команда: /goal <название>
        Или: /goal
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "🎯 **Создание цели**\n\n"
                "Использование:\n"
                "`/goal <название цели>`\n\n"
                "Примеры:\n"
                "`/goal Выучить 50 английских слов`\n"
                "`/goal Пробежать 5км`\n"
                "`/goal Закончить проект`\n\n"
                "После создания я помогу настроить детали!",
                parse_mode="Markdown"
            )
            return
        
        title = " ".join(context.args)
        
        # Создаем цель (пока без деталей)
        goal = await self.goals.create_goal(
            user_id=user.id,
            title=title,
            goal_type="custom"
        )
        
        response = f"""✅ **Цель создана!**

🎯 #{goal['id']}: {goal['title']}
📅 Тип: Пользовательская
⏰ Дедлайн: не указан
📊 Прогресс: 0%

**Что дальше?**
- `/goal_progress {goal['id']} <процент>` - обновить прогресс
- `/goal_details {goal['id']}` - детали цели
- `/goal_complete {goal['id']}` - отметить как выполненную
- `/goals` - список всех целей"""
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def goals_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показывает список целей
        
        Команда: /goals [active|completed|all]
        """
        user = update.effective_user
        
        filter_type = context.args[0] if context.args else "active"
        
        if filter_type == "active":
            goals = await self.goals.get_active_goals(user.id)
            title = "🎯 **Активные Цели**"
        elif filter_type == "completed":
            goals = [g for g in self.goals.goals_storage.get(user.id, []) if g["status"] == "completed"]
            title = "✅ **Выполненные Цели**"
        else:  # all
            goals = self.goals.goals_storage.get(user.id, [])
            title = "📋 **Все Цели**"
        
        if not goals:
            await update.message.reply_text(
                f"{title}\n\n"
                "Нет целей в этой категории.\n\n"
                "Создай новую цель: `/goal <название>`",
                parse_mode="Markdown"
            )
            return
        
        # Получаем статистику
        stats = await self.goals.get_statistics(user.id)
        
        response = f"""{title}

**Статистика:**
Всего целей: {stats['total_goals']}
Активных: {stats['active']}
Выполнено: {stats['completed']} ({stats['completion_rate']*100:.0f}%)
Серия: 🔥 {stats['current_streak']} дней

**Цели:**
"""
        
        for goal in goals:
            status_icons = {
                "active": "🎯",
                "completed": "✅",
                "failed": "❌",
                "paused": "⏸️"
            }
            
            icon = status_icons.get(goal["status"], "")
            progress_bar = self._get_progress_bar(goal["progress"])
            
            deadline_text = ""
            if goal.get("deadline"):
                deadline = datetime.fromisoformat(goal["deadline"])
                ukraine_tz = pytz.timezone('Europe/Kiev')
                now = datetime.now(ukraine_tz)
                
                if deadline.tzinfo is None:
                    deadline = ukraine_tz.localize(deadline)
                
                time_left = deadline - now
                
                if time_left.total_seconds() < 0:
                    deadline_text = " ⚠️ Просрочено"
                elif time_left.days == 0:
                    hours_left = int(time_left.total_seconds() / 3600)
                    deadline_text = f" ⏰ {hours_left}ч"
                elif time_left.days < 7:
                    deadline_text = f" 📅 {time_left.days}д"
            
            response += f"\n{icon} #{goal['id']}: **{goal['title']}**\n"
            response += f"   {progress_bar} {goal['progress']}%{deadline_text}\n"
        
        response += f"\n\n💪 {await self.goals.get_motivation_message(user.id)}"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def goal_progress_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обновляет прогресс цели
        
        Команда: /goal_progress <id> <процент>
        """
        user = update.effective_user
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Использование: `/goal_progress <id> <процент>`\n\n"
                "Пример: `/goal_progress 1 75`",
                parse_mode="Markdown"
            )
            return
        
        try:
            goal_id = int(context.args[0])
            progress = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ ID и прогресс должны быть числами")
            return
        
        goal = await self.goals.update_progress(user.id, goal_id, progress=progress)
        
        if not goal:
            await update.message.reply_text(f"❌ Цель #{goal_id} не найдена")
            return
        
        progress_bar = self._get_progress_bar(goal["progress"])
        
        response = f"""📊 **Прогресс обновлен!**

🎯 #{goal['id']}: {goal['title']}
{progress_bar} {goal['progress']}%
"""
        
        if goal["status"] == "completed":
            response += "\n\n🎉 **Поздравляю! Цель выполнена!** 🎉"
            
            # Получаем статистику для streak
            stats = await self.goals.get_statistics(user.id)
            if stats["current_streak"] >= 3:
                response += f"\n🔥 Серия: {stats['current_streak']} дней!"
        else:
            motivation = await self.goals.get_motivation_message(user.id)
            response += f"\n\n{motivation}"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def goal_complete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Отмечает цель как выполненную
        
        Команда: /goal_complete <id>
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "Использование: `/goal_complete <id>`\n\n"
                "Пример: `/goal_complete 1`",
                parse_mode="Markdown"
            )
            return
        
        try:
            goal_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом")
            return
        
        goal = await self.goals.complete_goal(user.id, goal_id)
        
        if not goal:
            await update.message.reply_text(f"❌ Цель #{goal_id} не найдена")
            return
        
        stats = await self.goals.get_statistics(user.id)
        
        response = f"""🎉 **Поздравляю! Цель выполнена!** 🎉

✅ {goal['title']}

**Твои достижения:**
Выполнено целей: {stats['completed']}
Процент выполнения: {stats['completion_rate']*100:.0f}%
"""
        
        if stats["current_streak"] >= 3:
            response += f"🔥 Серия: {stats['current_streak']} дней подряд!"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def goal_details_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показывает детали цели
        
        Команда: /goal_details <id>
        """
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "Использование: `/goal_details <id>`\n\n"
                "Пример: `/goal_details 1`",
                parse_mode="Markdown"
            )
            return
        
        try:
            goal_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом")
            return
        
        goal = await self.goals.get_goal(user.id, goal_id)
        
        if not goal:
            await update.message.reply_text(f"❌ Цель #{goal_id} не найдена")
            return
        
        status_text = {
            "active": "🎯 Активна",
            "completed": "✅ Выполнена",
            "failed": "❌ Провалена",
            "paused": "⏸️ На паузе"
        }
        
        type_text = {
            "daily": "☀️ Ежедневная",
            "weekly": "📅 Еженедельная",
            "monthly": "🏆 Ежемесячная",
            "custom": "🎯 Пользовательская"
        }
        
        progress_bar = self._get_progress_bar(goal["progress"])
        
        response = f"""📋 **Детали Цели**

🎯 #{goal['id']}: **{goal['title']}**

**Статус:** {status_text.get(goal['status'], goal['status'])}
**Тип:** {type_text.get(goal['type'], goal['type'])}
**Прогресс:** {progress_bar} {goal['progress']}%

**Создана:** {datetime.fromisoformat(goal['created_at']).strftime('%d.%m.%Y %H:%M')}
**Обновлена:** {datetime.fromisoformat(goal['last_updated']).strftime('%d.%m.%Y %H:%M')}
"""
        
        if goal.get("description"):
            response += f"**Описание:** {goal['description']}\n"
        
        if goal.get("deadline"):
            deadline = datetime.fromisoformat(goal["deadline"])
            ukraine_tz = pytz.timezone('Europe/Kiev')
            now = datetime.now(ukraine_tz)
            
            if deadline.tzinfo is None:
                deadline = ukraine_tz.localize(deadline)
            
            time_left = deadline - now
            
            deadline_str = deadline.strftime('%d.%m.%Y %H:%M')
            
            if time_left.total_seconds() < 0:
                response += f"**Дедлайн:** {deadline_str} ⚠️ Просрочен\n"
            else:
                days = time_left.days
                hours = int(time_left.seconds / 3600)
                response += f"**Дедлайн:** {deadline_str}\n"
                response += f"**Осталось:** {days}д {hours}ч\n"
        
        if goal.get("milestones"):
            response += f"\n**Этапы:**\n"
            for milestone in goal["milestones"]:
                if milestone in goal.get("completed_milestones", []):
                    response += f"✅ {milestone}\n"
                else:
                    response += f"⬜ {milestone}\n"
        
        response += f"\n**Команды:**\n"
        response += f"`/goal_progress {goal_id} <процент>` - обновить прогресс\n"
        response += f"`/goal_complete {goal_id}` - отметить выполненной\n"
        
        if goal["status"] == "active":
            response += f"`/goal_pause {goal_id}` - поставить на паузу\n"
        elif goal["status"] == "paused":
            response += f"`/goal_resume {goal_id}` - возобновить\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def goal_pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ставит цель на паузу"""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text("Использование: `/goal_pause <id>`", parse_mode="Markdown")
            return
        
        try:
            goal_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом")
            return
        
        goal = await self.goals.pause_goal(user.id, goal_id)
        
        if goal:
            await update.message.reply_text(
                f"⏸️ Цель **{goal['title']}** поставлена на паузу.\n\n"
                f"Возобновить: `/goal_resume {goal_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Цель #{goal_id} не найдена")
    
    async def goal_resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возобновляет цель"""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text("Использование: `/goal_resume <id>`", parse_mode="Markdown")
            return
        
        try:
            goal_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом")
            return
        
        goal = await self.goals.resume_goal(user.id, goal_id)
        
        if goal:
            await update.message.reply_text(
                f"▶️ Цель **{goal['title']}** возобновлена!\n\n"
                f"Продолжай работать над ней! 💪",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Цель #{goal_id} не найдена")
    
    async def goals_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показывает статистику по целям
        
        Команда: /goals_stats
        """
        user = update.effective_user
        
        stats = await self.goals.get_statistics(user.id)
        
        if stats["total_goals"] == 0:
            await update.message.reply_text(
                "📊 **Статистика Целей**\n\n"
                "У тебя пока нет целей.\n\n"
                "Создай первую: `/goal <название>`",
                parse_mode="Markdown"
            )
            return
        
        # Визуализация процента выполнения
        completion_bar = "█" * int(stats["completion_rate"] * 10) + "░" * (10 - int(stats["completion_rate"] * 10))
        
        response = f"""📊 **Статистика Целей**

**Всего целей:** {stats['total_goals']}
**Активных:** 🎯 {stats['active']}
**Выполнено:** ✅ {stats['completed']}
**Провалено:** ❌ {stats['failed']}
**На паузе:** ⏸️ {stats['paused']}

**Процент выполнения:**
{completion_bar} {stats['completion_rate']*100:.0f}%

**Достижений:** 🏆 {stats['achievements_count']}
**Серия:** 🔥 {stats['current_streak']} дней подряд
"""
        
        # Мотивационное сообщение
        motivation = await self.goals.get_motivation_message(user.id)
        response += f"\n\n{motivation}"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    
    def _get_progress_bar(self, progress: int) -> str:
        """Генерирует визуальный прогресс-бар"""
        filled = int(progress / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty

