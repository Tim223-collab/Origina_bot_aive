"""
Сервис управления целями и трекинга прогресса

Позволяет пользователям:
- Ставить краткосрочные и долгосрочные цели
- Отслеживать прогресс
- Получать мотивирующие сообщения
- Видеть статистику достижений
"""
from typing import Dict, List, Optional, Literal
from datetime import datetime, timedelta
import json
import pytz


GoalType = Literal["daily", "weekly", "monthly", "custom"]
GoalStatus = Literal["active", "completed", "failed", "paused"]


class GoalsService:
    """
    Сервис для управления целями пользователя
    """
    
    def __init__(self, db=None, ai=None):
        self.db = db
        self.ai = ai
        self.goals_storage = {}  # user_id -> List[Goal]
        self.achievements = {}  # user_id -> List[Achievement]
        
    async def create_goal(
        self,
        user_id: int,
        title: str,
        description: str = "",
        goal_type: GoalType = "custom",
        deadline: Optional[datetime] = None,
        milestones: List[str] = None
    ) -> Dict:
        """
        Создает новую цель
        
        Args:
            user_id: ID пользователя
            title: Название цели
            description: Описание
            goal_type: Тип цели (daily/weekly/monthly/custom)
            deadline: Дедлайн
            milestones: Список этапов
        
        Returns:
            Словарь с данными цели
        """
        if user_id not in self.goals_storage:
            self.goals_storage[user_id] = []
        
        # Автоматический дедлайн если не задан
        if deadline is None:
            ukraine_tz = pytz.timezone('Europe/Kiev')
            now = datetime.now(ukraine_tz)
            
            if goal_type == "daily":
                deadline = now.replace(hour=23, minute=59, second=59)
            elif goal_type == "weekly":
                days_until_sunday = (6 - now.weekday()) % 7
                deadline = (now + timedelta(days=days_until_sunday)).replace(hour=23, minute=59)
            elif goal_type == "monthly":
                next_month = now.replace(day=28) + timedelta(days=4)
                deadline = (next_month - timedelta(days=next_month.day-1)).replace(hour=23, minute=59)
        
        goal = {
            "id": len(self.goals_storage[user_id]) + 1,
            "title": title,
            "description": description,
            "type": goal_type,
            "status": "active",
            "progress": 0,
            "created_at": datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
            "deadline": deadline.isoformat() if deadline else None,
            "milestones": milestones or [],
            "completed_milestones": [],
            "last_updated": datetime.now(pytz.timezone('Europe/Kiev')).isoformat()
        }
        
        self.goals_storage[user_id].append(goal)
        
        # Сохраняем в БД если доступна
        if self.db:
            await self._save_goal_to_db(user_id, goal)
        
        return goal
    
    async def update_progress(
        self,
        user_id: int,
        goal_id: int,
        progress: int = None,
        milestone_completed: str = None
    ) -> Optional[Dict]:
        """
        Обновляет прогресс цели
        
        Args:
            user_id: ID пользователя
            goal_id: ID цели
            progress: Новый прогресс (0-100)
            milestone_completed: Название завершенного этапа
        
        Returns:
            Обновленная цель или None
        """
        goal = self._get_goal(user_id, goal_id)
        if not goal:
            return None
        
        # Обновляем прогресс
        if progress is not None:
            goal["progress"] = min(100, max(0, progress))
        
        # Отмечаем завершенный этап
        if milestone_completed and milestone_completed in goal["milestones"]:
            if milestone_completed not in goal["completed_milestones"]:
                goal["completed_milestones"].append(milestone_completed)
                
                # Автоматический расчет прогресса по этапам
                if goal["milestones"]:
                    milestone_progress = (len(goal["completed_milestones"]) / len(goal["milestones"])) * 100
                    goal["progress"] = int(milestone_progress)
        
        # Проверяем завершение
        if goal["progress"] >= 100:
            goal["status"] = "completed"
            await self._create_achievement(user_id, goal)
        
        goal["last_updated"] = datetime.now(pytz.timezone('Europe/Kiev')).isoformat()
        
        # Сохраняем в БД
        if self.db:
            await self._save_goal_to_db(user_id, goal)
        
        return goal
    
    async def get_active_goals(self, user_id: int, goal_type: Optional[GoalType] = None) -> List[Dict]:
        """
        Получает активные цели пользователя
        
        Args:
            user_id: ID пользователя
            goal_type: Фильтр по типу (опционально)
        
        Returns:
            Список активных целей
        """
        if user_id not in self.goals_storage:
            return []
        
        goals = [g for g in self.goals_storage[user_id] if g["status"] == "active"]
        
        if goal_type:
            goals = [g for g in goals if g["type"] == goal_type]
        
        # Сортируем по дедлайну
        goals.sort(key=lambda g: g.get("deadline") or "9999")
        
        return goals
    
    async def get_goal(self, user_id: int, goal_id: int) -> Optional[Dict]:
        """Получает цель по ID"""
        return self._get_goal(user_id, goal_id)
    
    def _get_goal(self, user_id: int, goal_id: int) -> Optional[Dict]:
        """Внутренний метод получения цели"""
        if user_id not in self.goals_storage:
            return None
        
        for goal in self.goals_storage[user_id]:
            if goal["id"] == goal_id:
                return goal
        
        return None
    
    async def complete_goal(self, user_id: int, goal_id: int) -> Optional[Dict]:
        """Помечает цель как завершенную"""
        goal = self._get_goal(user_id, goal_id)
        if not goal:
            return None
        
        goal["status"] = "completed"
        goal["progress"] = 100
        goal["last_updated"] = datetime.now(pytz.timezone('Europe/Kiev')).isoformat()
        
        # Создаем достижение
        await self._create_achievement(user_id, goal)
        
        # Сохраняем
        if self.db:
            await self._save_goal_to_db(user_id, goal)
        
        return goal
    
    async def pause_goal(self, user_id: int, goal_id: int) -> Optional[Dict]:
        """Ставит цель на паузу"""
        goal = self._get_goal(user_id, goal_id)
        if not goal:
            return None
        
        goal["status"] = "paused"
        goal["last_updated"] = datetime.now(pytz.timezone('Europe/Kiev')).isoformat()
        
        if self.db:
            await self._save_goal_to_db(user_id, goal)
        
        return goal
    
    async def resume_goal(self, user_id: int, goal_id: int) -> Optional[Dict]:
        """Возобновляет цель с паузы"""
        goal = self._get_goal(user_id, goal_id)
        if not goal:
            return None
        
        if goal["status"] == "paused":
            goal["status"] = "active"
            goal["last_updated"] = datetime.now(pytz.timezone('Europe/Kiev')).isoformat()
            
            if self.db:
                await self._save_goal_to_db(user_id, goal)
        
        return goal
    
    async def delete_goal(self, user_id: int, goal_id: int) -> bool:
        """Удаляет цель"""
        if user_id not in self.goals_storage:
            return False
        
        goal = self._get_goal(user_id, goal_id)
        if goal:
            self.goals_storage[user_id].remove(goal)
            
            # Удаляем из БД
            if self.db:
                await self._delete_goal_from_db(user_id, goal_id)
            
            return True
        
        return False
    
    async def check_deadlines(self, user_id: int) -> List[Dict]:
        """
        Проверяет дедлайны и возвращает просроченные/близкие цели
        
        Returns:
            [
                {
                    "goal": goal_dict,
                    "status": "overdue" | "due_soon" | "due_today",
                    "time_left": timedelta
                }
            ]
        """
        ukraine_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(ukraine_tz)
        
        active_goals = await self.get_active_goals(user_id)
        alerts = []
        
        for goal in active_goals:
            if not goal.get("deadline"):
                continue
            
            deadline = datetime.fromisoformat(goal["deadline"])
            if deadline.tzinfo is None:
                deadline = ukraine_tz.localize(deadline)
            
            time_left = deadline - now
            
            if time_left.total_seconds() < 0:
                # Просрочено
                goal["status"] = "failed"
                alerts.append({
                    "goal": goal,
                    "status": "overdue",
                    "time_left": time_left
                })
            elif time_left.total_seconds() < 3600:  # Меньше часа
                alerts.append({
                    "goal": goal,
                    "status": "due_soon",
                    "time_left": time_left
                })
            elif time_left.days == 0:  # Сегодня
                alerts.append({
                    "goal": goal,
                    "status": "due_today",
                    "time_left": time_left
                })
        
        return alerts
    
    async def get_statistics(self, user_id: int) -> Dict:
        """
        Получает статистику по целям
        
        Returns:
            {
                "total_goals": 10,
                "active": 3,
                "completed": 6,
                "failed": 1,
                "completion_rate": 0.6,
                "achievements_count": 5,
                "current_streak": 3
            }
        """
        if user_id not in self.goals_storage:
            return {
                "total_goals": 0,
                "active": 0,
                "completed": 0,
                "failed": 0,
                "paused": 0,
                "completion_rate": 0.0,
                "achievements_count": 0,
                "current_streak": 0
            }
        
        goals = self.goals_storage[user_id]
        
        active = len([g for g in goals if g["status"] == "active"])
        completed = len([g for g in goals if g["status"] == "completed"])
        failed = len([g for g in goals if g["status"] == "failed"])
        paused = len([g for g in goals if g["status"] == "paused"])
        
        total = len(goals)
        completion_rate = completed / total if total > 0 else 0.0
        
        achievements_count = len(self.achievements.get(user_id, []))
        
        # Подсчет текущей серии (streak)
        current_streak = await self._calculate_streak(user_id)
        
        return {
            "total_goals": total,
            "active": active,
            "completed": completed,
            "failed": failed,
            "paused": paused,
            "completion_rate": completion_rate,
            "achievements_count": achievements_count,
            "current_streak": current_streak
        }
    
    async def get_motivation_message(self, user_id: int) -> str:
        """
        Генерирует мотивационное сообщение на основе прогресса
        """
        stats = await self.get_statistics(user_id)
        active_goals = await self.get_active_goals(user_id)
        
        if not active_goals:
            return "🎯 Пора поставить новые цели! Используй /goal для создания."
        
        # Средний прогресс по активным целям
        avg_progress = sum(g["progress"] for g in active_goals) / len(active_goals)
        
        if avg_progress >= 75:
            messages = [
                f"🚀 Отличная работа! Ты на {avg_progress:.0f}% пути к своим целям!",
                f"💪 Ты почти у цели! Осталось совсем чуть-чуть!",
                f"⭐ Невероятный прогресс - {avg_progress:.0f}%! Продолжай!",
            ]
        elif avg_progress >= 50:
            messages = [
                f"👍 Хороший прогресс - {avg_progress:.0f}%! Ты на правильном пути!",
                f"🎯 Половина пути пройдена! Так держать!",
                f"✨ {avg_progress:.0f}% выполнено. Продолжаем!",
            ]
        elif avg_progress >= 25:
            messages = [
                f"🌱 Хорошее начало! {avg_progress:.0f}% уже сделано!",
                f"💫 Каждый день ты на шаг ближе к цели!",
                f"🔥 Продолжай в том же духе! Уже {avg_progress:.0f}%!",
            ]
        else:
            messages = [
                "🎯 Начинаем движение к целям! Первый шаг - самый важный!",
                "💪 Давай начнем! Каждый маленький шаг приближает к цели!",
                "✨ Пора действовать! У тебя всё получится!",
            ]
        
        # Добавляем инфо о streak
        if stats["current_streak"] >= 3:
            messages[0] += f"\n🔥 Серия: {stats['current_streak']} дней!"
        
        import random
        return random.choice(messages)
    
    async def _create_achievement(self, user_id: int, goal: Dict):
        """Создает достижение за выполненную цель"""
        if user_id not in self.achievements:
            self.achievements[user_id] = []
        
        achievement = {
            "id": len(self.achievements[user_id]) + 1,
            "title": f"Выполнена цель: {goal['title']}",
            "description": goal.get("description", ""),
            "earned_at": datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
            "goal_id": goal["id"],
            "icon": self._get_achievement_icon(goal)
        }
        
        self.achievements[user_id].append(achievement)
    
    def _get_achievement_icon(self, goal: Dict) -> str:
        """Возвращает иконку достижения в зависимости от типа цели"""
        icons = {
            "daily": "☀️",
            "weekly": "📅",
            "monthly": "🏆",
            "custom": "⭐"
        }
        return icons.get(goal["type"], "🎯")
    
    async def _calculate_streak(self, user_id: int) -> int:
        """Подсчитывает текущую серию выполненных целей"""
        if user_id not in self.goals_storage:
            return 0
        
        # Получаем завершенные цели, отсортированные по дате
        completed_goals = [
            g for g in self.goals_storage[user_id]
            if g["status"] == "completed"
        ]
        completed_goals.sort(key=lambda g: g["last_updated"], reverse=True)
        
        if not completed_goals:
            return 0
        
        # Считаем непрерывную серию дней с завершенными целями
        streak = 0
        ukraine_tz = pytz.timezone('Europe/Kiev')
        today = datetime.now(ukraine_tz).date()
        
        current_date = today
        for goal in completed_goals:
            goal_date = datetime.fromisoformat(goal["last_updated"]).date()
            
            if goal_date == current_date or goal_date == current_date - timedelta(days=1):
                streak += 1
                current_date = goal_date - timedelta(days=1)
            else:
                break
        
        return streak
    
    async def _save_goal_to_db(self, user_id: int, goal: Dict):
        """Сохраняет цель в БД (заглушка для будущей реализации)"""
        # TODO: реализовать когда добавим таблицу goals
        pass
    
    async def _delete_goal_from_db(self, user_id: int, goal_id: int):
        """Удаляет цель из БД (заглушка)"""
        # TODO: реализовать
        pass
    
    async def smart_goal_suggestion(self, user_id: int, user_message: str) -> Optional[Dict]:
        """
        Умное предложение цели на основе сообщения пользователя
        
        Использует AI для анализа намерений и предложения цели
        """
        if not self.ai:
            return None
        
        prompt = f"""Проанализируй сообщение пользователя и определи, хочет ли он поставить цель.

Сообщение: "{user_message}"

Если в сообщении есть намерение поставить цель, верни JSON:
{{
    "has_goal": true,
    "title": "Краткое название цели",
    "description": "Описание",
    "type": "daily|weekly|monthly|custom",
    "milestones": ["этап1", "этап2", ...]
}}

Если нет намерения - верни:
{{
    "has_goal": false
}}

JSON:"""
        
        try:
            response = await self.ai.extract_json(prompt)
            if response and response.get("has_goal"):
                return response
        except Exception as e:
            print(f"❌ Ошибка smart_goal_suggestion: {e}")
        
        return None

