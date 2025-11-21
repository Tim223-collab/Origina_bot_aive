"""
Сервис мониторинга отключений электроэнергии ДТЕК

Проактивно отслеживает графики и уведомляет пользователя
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import pytz
from services.parsers.parser_factory import ParserFactory
import logging


logger = logging.getLogger(__name__)


class DTEKMonitorService:
    """
    Сервис для проактивного мониторинга отключений ДТЕК
    """
    
    def __init__(self, db=None):
        self.db = db
        self.parser = None
        self.user_addresses = {}  # user_id -> address_config
        self.monitoring_tasks = {}  # user_id -> asyncio.Task
        self.last_notifications = {}  # user_id -> {type: datetime}
        
    async def initialize_parser(self, address_config: Dict) -> bool:
        """
        Инициализирует парсер с адресом пользователя
        
        Args:
            address_config: {
                "city": "м. Дніпро",
                "street": "вул. Калинова",
                "building": "47",
                "queue": "1.2"
            }
        """
        try:
            self.parser = await ParserFactory.create_parser(
                name="dtek",
                config_data=address_config,
                auto_init=True
            )
            
            if not self.parser:
                logger.error("❌ Failed to create DTEK parser")
                return False
            
            # Авторизация (для ДТЕК - просто загрузка страницы)
            if not await self.parser.login():
                logger.error("❌ Failed to load DTEK page")
                return False
            
            logger.info(f"✅ DTEK parser initialized for {address_config.get('street')}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Parser initialization error: {e}")
            return False
    
    async def get_current_status(self, user_id: int) -> Dict:
        """
        Получает текущий статус отключений
        
        Returns:
            {
                "success": True,
                "has_shutdown_now": False,
                "message": "✅ Сейчас свет есть",
                "today_shutdowns": ["14:00-14:30", "18:00-18:30"]
            }
        """
        if not self.parser:
            address = self.user_addresses.get(user_id)
            if not address:
                return {
                    "success": False,
                    "error": "Адрес не настроен. Используй /dtek_setup"
                }
            
            if not await self.initialize_parser(address):
                return {
                    "success": False,
                    "error": "Не удалось инициализировать парсер"
                }
        
        try:
            result = await self.parser.parse(operation="check_now")
            return result
        except Exception as e:
            logger.error(f"❌ Error checking current status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Закрываем парсер после использования
            if self.parser:
                await self.parser.close()
                self.parser = None
    
    async def get_today_schedule(self, user_id: int) -> Dict:
        """Получает график на сегодня"""
        if not self.parser:
            address = self.user_addresses.get(user_id)
            if not address:
                return {
                    "success": False,
                    "error": "Адрес не настроен"
                }
            
            if not await self.initialize_parser(address):
                return {
                    "success": False,
                    "error": "Не удалось инициализировать парсер"
                }
        
        try:
            result = await self.parser.parse(operation="check_today")
            return result
        except Exception as e:
            logger.error(f"❌ Error getting today schedule: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if self.parser:
                await self.parser.close()
                self.parser = None
    
    async def get_week_schedule(self, user_id: int) -> Dict:
        """Получает график на неделю"""
        if not self.parser:
            address = self.user_addresses.get(user_id)
            if not address:
                return {
                    "success": False,
                    "error": "Адрес не настроен"
                }
            
            if not await self.initialize_parser(address):
                return {
                    "success": False,
                    "error": "Не удалось инициализировать парсер"
                }
        
        try:
            result = await self.parser.parse(operation="get_schedule", days=7)
            return result
        except Exception as e:
            logger.error(f"❌ Error getting week schedule: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if self.parser:
                await self.parser.close()
                self.parser = None
    
    async def check_for_changes(self, user_id: int) -> Dict:
        """Проверяет изменения в графике"""
        if not self.parser:
            address = self.user_addresses.get(user_id)
            if not address:
                return {
                    "success": False,
                    "error": "Адрес не настроен"
                }
            
            if not await self.initialize_parser(address):
                return {
                    "success": False,
                    "error": "Не удалось инициализировать парсер"
                }
        
        try:
            result = await self.parser.parse(operation="track_changes")
            return result
        except Exception as e:
            logger.error(f"❌ Error tracking changes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if self.parser:
                await self.parser.close()
                self.parser = None
    
    def set_user_address(
        self,
        user_id: int,
        city: str,
        street: str,
        building: str,
        queue: str = None
    ):
        """Сохраняет адрес пользователя"""
        self.user_addresses[user_id] = {
            "city": city,
            "street": street,
            "building": building,
            "queue": queue
        }
        logger.info(f"✅ Address saved for user {user_id}: {street}, {building}")
    
    def get_user_address(self, user_id: int) -> Optional[Dict]:
        """Получает адрес пользователя"""
        return self.user_addresses.get(user_id)
    
    async def start_monitoring(self, user_id: int, bot, check_interval: int = 3600):
        """
        Запускает проактивный мониторинг для пользователя
        
        Args:
            user_id: ID пользователя
            bot: Telegram bot для отправки уведомлений
            check_interval: Интервал проверки в секундах (по умолчанию 1 час)
        """
        if user_id in self.monitoring_tasks:
            logger.warning(f"⚠️ Monitoring already running for user {user_id}")
            return
        
        task = asyncio.create_task(
            self._monitoring_loop(user_id, bot, check_interval)
        )
        self.monitoring_tasks[user_id] = task
        logger.info(f"✅ Monitoring started for user {user_id}")
    
    async def stop_monitoring(self, user_id: int):
        """Останавливает мониторинг"""
        if user_id in self.monitoring_tasks:
            task = self.monitoring_tasks[user_id]
            task.cancel()
            del self.monitoring_tasks[user_id]
            logger.info(f"⏸️ Monitoring stopped for user {user_id}")
    
    async def _monitoring_loop(self, user_id: int, bot, check_interval: int):
        """Основной цикл мониторинга"""
        while True:
            try:
                # Проверяем изменения
                changes_result = await self.check_for_changes(user_id)
                
                if changes_result.get("success") and changes_result.get("has_changes"):
                    # Есть изменения - уведомляем
                    await self._send_change_notification(user_id, bot, changes_result)
                
                # Проверяем приближающиеся отключения
                await self._check_upcoming_shutdowns(user_id, bot)
                
                # Ждем до следующей проверки
                await asyncio.sleep(check_interval)
            
            except asyncio.CancelledError:
                logger.info(f"🛑 Monitoring cancelled for user {user_id}")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error for user {user_id}: {e}")
                await asyncio.sleep(check_interval)
    
    async def _send_change_notification(self, user_id: int, bot, changes_result: Dict):
        """Отправляет уведомление об изменениях в графике"""
        try:
            changes = changes_result.get("changes", [])
            
            message = "⚡ **Изменения в графике отключений!**\n\n"
            
            for change in changes:
                date = change.get("date")
                change_type = change.get("type")
                
                if change_type == "added":
                    times = ", ".join(change.get("shutdown_times", []))
                    message += f"📅 **{date}**\n➕ Добавлены отключения: {times}\n\n"
                
                elif change_type == "modified":
                    added = change.get("added_times", [])
                    removed = change.get("removed_times", [])
                    
                    message += f"📅 **{date}**\n"
                    if added:
                        message += f"➕ Добавлены: {', '.join(added)}\n"
                    if removed:
                        message += f"➖ Убраны: {', '.join(removed)}\n"
                    message += "\n"
            
            message += "Проверь актуальный график: /dtek_today"
            
            await bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
            logger.info(f"✅ Change notification sent to user {user_id}")
        
        except Exception as e:
            logger.error(f"❌ Error sending change notification: {e}")
    
    async def _check_upcoming_shutdowns(self, user_id: int, bot):
        """Проверяет и уведомляет о приближающихся отключениях"""
        try:
            # Получаем график на сегодня
            today_result = await self.get_today_schedule(user_id)
            
            if not today_result.get("success"):
                return
            
            schedule = today_result.get("schedule")
            if not schedule or not schedule.get("has_shutdowns"):
                return
            
            # Текущее время
            kiev_tz = pytz.timezone('Europe/Kiev')
            now = datetime.now(kiev_tz)
            current_time = now.strftime("%H:%M")
            
            # Проверяем отключения в ближайшие 30 минут
            upcoming = []
            for time_slot in schedule.get("shutdown_times", []):
                # Парсим время начала (например "14:00-14:30" -> "14:00")
                import re
                match = re.search(r'(\d{2}):(\d{2})', time_slot)
                if match:
                    slot_hour = int(match.group(1))
                    slot_minute = int(match.group(2))
                    
                    slot_time = now.replace(hour=slot_hour, minute=slot_minute, second=0)
                    time_diff = (slot_time - now).total_seconds() / 60
                    
                    # Если отключение через 15-30 минут
                    if 15 <= time_diff <= 30:
                        # Проверяем, не отправляли ли уже уведомление
                        last_notif = self.last_notifications.get(user_id, {}).get(time_slot)
                        if not last_notif or (now - last_notif).total_seconds() > 3600:
                            upcoming.append(time_slot)
                            
                            # Сохраняем время уведомления
                            if user_id not in self.last_notifications:
                                self.last_notifications[user_id] = {}
                            self.last_notifications[user_id][time_slot] = now
            
            # Отправляем уведомление
            if upcoming:
                message = f"⚠️ **Скоро отключение света!**\n\n"
                message += f"Через 15-30 минут отключат свет:\n"
                for time_slot in upcoming:
                    message += f"⚡ {time_slot}\n"
                message += f"\nПодготовься заранее! 💡"
                
                await bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                logger.info(f"✅ Upcoming shutdown notification sent to user {user_id}")
        
        except Exception as e:
            logger.error(f"❌ Error checking upcoming shutdowns: {e}")

