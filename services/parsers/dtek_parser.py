"""
Парсер для ДТЕК Дніпровські Електромережі
Отслеживание графиков отключений электроэнергии

URL: https://www.dtek-dnem.com.ua/ua/shutdowns
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_parser import BaseParser
from playwright.async_api import TimeoutError as PlaywrightTimeout
import logging
import pytz
import re


logger = logging.getLogger(__name__)


class DTEKParser(BaseParser):
    """
    Парсер для ДТЕК - графики отключений электроэнергии
    """
    
    NAME = "dtek"
    DESCRIPTION = "Парсер графиков отключений ДТЕК Дніпровські Електромережі"
    VERSION = "1.0.0"
    SUPPORTED_OPERATIONS = ["get_schedule", "check_now", "check_today", "track_changes"]
    
    def __init__(self, config_data: Dict[str, Any] = None):
        super().__init__(config_data)
        
        self.base_url = "https://www.dtek-dnem.com.ua/ua/shutdowns"
        
        # Адрес пользователя (можно задать в конфиге)
        self.user_address = config_data or {}
        self.city = self.user_address.get("city", "м. Дніпро")
        self.street = self.user_address.get("street", "")
        self.building = self.user_address.get("building", "")
        self.queue = self.user_address.get("queue", "")  # Черга (например "1.2")
        
        # Кэш графика (для отслеживания изменений)
        self.cached_schedule = None
        self.last_check_time = None
        
        # CSS селекторы
        self.SELECTORS = {
            "city_input": "input[placeholder*='нас. пункт']",
            "city_dropdown": "div[role='option']",
            "street_input": "input[placeholder*='вулицю']",
            "street_dropdown": "div[role='option']",
            "building_input": "input[placeholder*='номер']",
            "queue_input": "input[placeholder*='Черга']",
            
            "schedule_table": "table",
            "schedule_rows": "tbody tr",
            "time_cells": "td",
            "warning_box": ".alert-warning, .warning-box",
            "info_text": "p, div.info",
            
            "today_button": "button:has-text('на сьогодні')",
            "tomorrow_button": "button:has-text('на завтра')",
        }
    
    async def validate_config(self) -> bool:
        """Проверяет валидность конфигурации"""
        # Для ДТЕК не обязательны credentials, но нужен адрес
        if not self.street or not self.building:
            logger.warning("⚠️ Адрес не полностью настроен. Укажи улицу и номер дома.")
            return False
        return True
    
    async def login(self) -> bool:
        """ДТЕК не требует авторизации"""
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            logger.info("✅ ДТЕК page loaded")
            return True
        except Exception as e:
            logger.error(f"❌ ДТЕК page load error: {e}")
            return False
    
    async def parse(self, operation: str = "get_schedule", **kwargs) -> Dict[str, Any]:
        """
        Основной метод парсинга
        
        Args:
            operation: Тип операции
                - get_schedule: получить график на неделю
                - check_now: проверить текущий статус
                - check_today: график на сегодня
                - track_changes: отследить изменения
            **kwargs: Дополнительные параметры
        
        Returns:
            Результаты парсинга
        """
        if operation == "get_schedule":
            return await self._get_schedule(**kwargs)
        elif operation == "check_now":
            return await self._check_now(**kwargs)
        elif operation == "check_today":
            return await self._check_today(**kwargs)
        elif operation == "track_changes":
            return await self._track_changes(**kwargs)
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "supported": self.SUPPORTED_OPERATIONS
            }
    
    async def _fill_address_form(self) -> bool:
        """Заполняет форму с адресом"""
        try:
            # Город
            city_input = await self.page.wait_for_selector(
                self.SELECTORS["city_input"],
                timeout=5000
            )
            await city_input.fill(self.city)
            await self.page.wait_for_timeout(500)
            
            # Выбираем из dropdown
            city_option = await self.page.wait_for_selector(
                f"{self.SELECTORS['city_dropdown']}:has-text('{self.city}')",
                timeout=3000
            )
            await city_option.click()
            await self.page.wait_for_timeout(500)
            
            # Улица
            street_input = await self.page.wait_for_selector(
                self.SELECTORS["street_input"],
                timeout=5000
            )
            await street_input.fill(self.street)
            await self.page.wait_for_timeout(500)
            
            street_option = await self.page.wait_for_selector(
                f"{self.SELECTORS['street_dropdown']}:has-text('{self.street}')",
                timeout=3000
            )
            await street_option.click()
            await self.page.wait_for_timeout(500)
            
            # Номер дома
            building_input = await self.page.wait_for_selector(
                self.SELECTORS["building_input"],
                timeout=5000
            )
            await building_input.fill(self.building)
            await self.page.wait_for_timeout(500)
            
            # Если указана черга
            if self.queue:
                queue_input = await self.page.wait_for_selector(
                    self.SELECTORS["queue_input"],
                    timeout=5000
                )
                await queue_input.fill(self.queue)
                await self.page.wait_for_timeout(500)
            
            # Ждем загрузку графика
            await self.page.wait_for_timeout(2000)
            
            logger.info(f"✅ Форма заполнена: {self.city}, {self.street}, {self.building}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка заполнения формы: {e}")
            return False
    
    async def _get_schedule(self, days: int = 7) -> Dict[str, Any]:
        """
        Получает график отключений на указанное количество дней
        
        Args:
            days: Количество дней (по умолчанию 7)
        
        Returns:
            График отключений
        """
        try:
            # Заполняем форму
            if not await self._fill_address_form():
                return {
                    "success": False,
                    "error": "Не удалось заполнить форму адреса"
                }
            
            # Парсим таблицу с графиком
            schedule = await self._parse_schedule_table()
            
            # Проверяем предупреждения
            warnings = await self._get_warnings()
            
            result = {
                "success": True,
                "address": {
                    "city": self.city,
                    "street": self.street,
                    "building": self.building,
                    "queue": self.queue
                },
                "schedule": schedule,
                "warnings": warnings,
                "parsed_at": datetime.now(pytz.timezone('Europe/Kiev')).isoformat()
            }
            
            # Кэшируем для отслеживания изменений
            self.cached_schedule = result
            self.last_check_time = datetime.now()
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения графика: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _parse_schedule_table(self) -> List[Dict[str, Any]]:
        """Парсит таблицу с графиком отключений"""
        try:
            schedule = []
            
            # Находим таблицу
            table = await self.page.query_selector(self.SELECTORS["schedule_table"])
            if not table:
                return []
            
            # Получаем все временные слоты (часы)
            header_row = await table.query_selector("thead tr")
            time_headers = []
            if header_row:
                cells = await header_row.query_selector_all("th")
                for cell in cells[1:]:  # Пропускаем первую колонку (дата)
                    time_text = await cell.inner_text()
                    time_headers.append(time_text.strip())
            
            # Парсим строки с днями
            rows = await table.query_selector_all(self.SELECTORS["schedule_rows"])
            
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 2:
                    continue
                
                # Первая ячейка - дата
                date_cell = cells[0]
                date_text = await date_cell.inner_text()
                
                # Остальные ячейки - статус отключений
                shutdowns = []
                for i, cell in enumerate(cells[1:]):
                    # Проверяем наличие иконки отключения
                    has_shutdown = await cell.query_selector("svg, i, .shutdown-icon")
                    
                    if has_shutdown:
                        time_slot = time_headers[i] if i < len(time_headers) else f"Слот {i+1}"
                        shutdowns.append(time_slot)
                
                schedule.append({
                    "date": self._parse_date(date_text),
                    "date_text": date_text.strip(),
                    "has_shutdowns": len(shutdowns) > 0,
                    "shutdown_times": shutdowns
                })
            
            return schedule
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга таблицы: {e}")
            return []
    
    def _parse_date(self, date_text: str) -> str:
        """Парсит дату из текста"""
        # Пример: "21.11 ПТ" -> "2024-11-21"
        try:
            match = re.search(r'(\d{2})\.(\d{2})', date_text)
            if match:
                day = match.group(1)
                month = match.group(2)
                year = datetime.now().year
                return f"{year}-{month}-{day}"
        except:
            pass
        
        return date_text
    
    async def _get_warnings(self) -> List[str]:
        """Получает предупреждения с сайта"""
        try:
            warnings = []
            
            warning_boxes = await self.page.query_selector_all(self.SELECTORS["warning_box"])
            for box in warning_boxes:
                text = await box.inner_text()
                if text.strip():
                    warnings.append(text.strip())
            
            return warnings
        except:
            return []
    
    async def _check_now(self) -> Dict[str, Any]:
        """Проверяет текущий статус (есть ли сейчас отключение)"""
        try:
            schedule = await self._get_schedule(days=1)
            
            if not schedule["success"]:
                return schedule
            
            # Текущее время в Киеве
            kiev_tz = pytz.timezone('Europe/Kiev')
            now = datetime.now(kiev_tz)
            current_hour = now.hour
            current_date = now.strftime("%Y-%m-%d")
            
            # Ищем сегодняшний день в графике
            today_schedule = None
            for day in schedule["schedule"]:
                if day["date"] == current_date:
                    today_schedule = day
                    break
            
            if not today_schedule:
                return {
                    "success": True,
                    "has_shutdown_now": False,
                    "message": "График на сегодня не найден"
                }
            
            # Проверяем текущий час
            has_shutdown_now = False
            for time_slot in today_schedule.get("shutdown_times", []):
                # Парсим время (например "14:00-14:30")
                if self._is_current_time_in_slot(time_slot, current_hour):
                    has_shutdown_now = True
                    break
            
            return {
                "success": True,
                "has_shutdown_now": has_shutdown_now,
                "current_time": now.strftime("%H:%M"),
                "today_shutdowns": today_schedule.get("shutdown_times", []),
                "message": "⚡ Сейчас отключение!" if has_shutdown_now else "✅ Сейчас свет есть"
            }
        
        except Exception as e:
            logger.error(f"❌ Ошибка проверки текущего статуса: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _is_current_time_in_slot(self, time_slot: str, current_hour: int) -> bool:
        """Проверяет попадает ли текущее время в слот"""
        try:
            # Парсим время из слота (например "14:00-14:30" или "14:00")
            match = re.search(r'(\d{2}):(\d{2})', time_slot)
            if match:
                slot_hour = int(match.group(1))
                return slot_hour == current_hour
        except:
            pass
        
        return False
    
    async def _check_today(self) -> Dict[str, Any]:
        """Возвращает график на сегодня"""
        schedule = await self._get_schedule(days=1)
        
        if not schedule["success"]:
            return schedule
        
        kiev_tz = pytz.timezone('Europe/Kiev')
        today = datetime.now(kiev_tz).strftime("%Y-%m-%d")
        
        today_schedule = None
        for day in schedule["schedule"]:
            if day["date"] == today:
                today_schedule = day
                break
        
        return {
            "success": True,
            "date": today,
            "schedule": today_schedule,
            "warnings": schedule.get("warnings", [])
        }
    
    async def _track_changes(self) -> Dict[str, Any]:
        """
        Отслеживает изменения в графике
        
        Returns:
            Информация об изменениях
        """
        try:
            # Получаем новый график
            new_schedule = await self._get_schedule()
            
            if not new_schedule["success"]:
                return new_schedule
            
            # Если нет кэша - это первая проверка
            if not self.cached_schedule:
                return {
                    "success": True,
                    "has_changes": False,
                    "message": "Первая проверка, кэш создан",
                    "schedule": new_schedule
                }
            
            # Сравниваем графики
            changes = self._compare_schedules(
                self.cached_schedule["schedule"],
                new_schedule["schedule"]
            )
            
            result = {
                "success": True,
                "has_changes": len(changes) > 0,
                "changes": changes,
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "current_schedule": new_schedule
            }
            
            # Обновляем кэш
            self.cached_schedule = new_schedule
            self.last_check_time = datetime.now()
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Ошибка отслеживания изменений: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _compare_schedules(
        self,
        old_schedule: List[Dict],
        new_schedule: List[Dict]
    ) -> List[Dict]:
        """Сравнивает два графика и находит изменения"""
        changes = []
        
        # Создаем словарь старого графика по датам
        old_by_date = {day["date"]: day for day in old_schedule}
        
        for new_day in new_schedule:
            date = new_day["date"]
            old_day = old_by_date.get(date)
            
            if not old_day:
                # Новый день добавлен
                if new_day["has_shutdowns"]:
                    changes.append({
                        "type": "added",
                        "date": date,
                        "shutdown_times": new_day["shutdown_times"]
                    })
                continue
            
            # Сравниваем время отключений
            old_times = set(old_day.get("shutdown_times", []))
            new_times = set(new_day.get("shutdown_times", []))
            
            added_times = new_times - old_times
            removed_times = old_times - new_times
            
            if added_times or removed_times:
                changes.append({
                    "type": "modified",
                    "date": date,
                    "added_times": list(added_times),
                    "removed_times": list(removed_times)
                })
        
        return changes

