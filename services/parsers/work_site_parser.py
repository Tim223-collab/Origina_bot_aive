"""
Парсер для рабочего сайта с отчетами работников

Адаптирует существующий WorkParserService под новую архитектуру
"""
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from .base_parser import BaseParser
from playwright.async_api import TimeoutError as PlaywrightTimeout
import logging
import config


logger = logging.getLogger(__name__)


class WorkSiteParser(BaseParser):
    """
    Парсер для рабочего сайта
    """
    
    NAME = "work_site"
    DESCRIPTION = "Парсер рабочего сайта с отчетами работников"
    VERSION = "2.0.0"
    SUPPORTED_OPERATIONS = ["get_stats", "get_worker_details", "get_daily_report"]
    
    def __init__(self, config_data: Dict[str, Any] = None):
        super().__init__(config_data)
        
        # Получаем credentials из config или из config_data
        self.base_url = config_data.get("url") if config_data else config.WORK_SITE_URL
        self.username = config_data.get("username") if config_data else config.WORK_SITE_USERNAME
        self.password = config_data.get("password") if config_data else config.WORK_SITE_PASSWORD
        
        # CSS селекторы
        self.SELECTORS = {
            # Авторизация
            "login_username": "input[name='username']",
            "login_password": "input[name='password']",
            "login_submit": "button[type='submit']",
            
            # Фильтры
            "date_filter": "input#report_date",
            "team_good_bunny": "button[data-team='2']",
            "team_velvet": "button[data-team='1']",
            
            # Таблица
            "table_rows": "tbody tr",
            "worker_name": "td:nth-child(1) strong",
            "worker_username": "td:nth-child(1) small",
            "team_badge": "td:nth-child(2) .badge",
            "report_date": "td:nth-child(3) strong",
            "report_id": "td:nth-child(3) small",
            
            # Иконки скама
            "scam_icon_red": "td:nth-child(4) i.bi-x-circle-fill.text-danger",
            "scam_icon_yellow": "td:nth-child(4) i.bi-exclamation-triangle-fill.text-warning",
            "scam_icon_green": "td:nth-child(4) i.bi-check-circle-fill.text-success",
            "scam_details_btn": "td:nth-child(4) button[id^='blacklist-btn-']",
            
            # Числовые показатели
            "sfs_badge": "td:nth-child(5) .badge",
            "only_now_badge": "td:nth-child(6) .badge",
            "sch_badge": "td:nth-child(7) .badge",
            "created_at": "td:nth-child(8) small",
            
            # Модальное окно
            "modal": "#blacklistModalDynamic",
            "modal_body": "#blacklistModalDynamic .modal-body",
            "modal_close": "#blacklistModalDynamic .btn-close",
        }
    
    async def validate_config(self) -> bool:
        """Проверяет валидность конфигурации"""
        return all([self.base_url, self.username, self.password])
    
    async def login(self) -> bool:
        """Авторизация на сайте"""
        if not await self.validate_config():
            logger.error("❌ Invalid config for WorkSiteParser")
            return False
        
        try:
            # Переходим на страницу логина
            await self.page.goto(self.base_url, wait_until="networkidle")
            
            # Заполняем форму
            await self.page.fill(self.SELECTORS["login_username"], self.username)
            await self.page.fill(self.SELECTORS["login_password"], self.password)
            
            # Отправляем
            await self.page.click(self.SELECTORS["login_submit"])
            await self.page.wait_for_load_state("networkidle")
            
            # Проверяем успешность
            current_url = self.page.url
            if "/login" not in current_url:
                logger.info("✅ WorkSite login successful")
                return True
            else:
                logger.error("❌ WorkSite login failed")
                return False
        
        except Exception as e:
            logger.error(f"❌ WorkSite login error: {e}")
            return False
    
    async def parse(self, operation: str = "get_stats", **kwargs) -> Dict[str, Any]:
        """
        Основной метод парсинга
        
        Args:
            operation: Тип операции (get_stats, get_worker_details, etc.)
            **kwargs: Дополнительные параметры
        
        Returns:
            Результаты парсинга
        """
        if operation == "get_stats":
            return await self._get_stats(**kwargs)
        elif operation == "get_worker_details":
            return await self._get_worker_details(**kwargs)
        elif operation == "get_daily_report":
            return await self._get_daily_report(**kwargs)
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "supported": self.SUPPORTED_OPERATIONS
            }
    
    async def _get_stats(
        self,
        report_date: Optional[str] = None,
        team: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает статистику работников
        
        Args:
            report_date: Дата отчета (YYYY-MM-DD) или None для сегодня
            team: Команда ("good_bunny" или "velvet") или None для всех
        
        Returns:
            Словарь со статистикой
        """
        try:
            # Применяем фильтры если нужно
            if report_date:
                await self.page.fill(self.SELECTORS["date_filter"], report_date)
                await self.page.press(self.SELECTORS["date_filter"], "Enter")
                await self.page.wait_for_timeout(1000)
            
            if team:
                team_selector = (
                    self.SELECTORS["team_good_bunny"] if team == "good_bunny"
                    else self.SELECTORS["team_velvet"]
                )
                await self.page.click(team_selector)
                await self.page.wait_for_timeout(1000)
            
            # Парсим таблицу
            rows = await self.page.query_selector_all(self.SELECTORS["table_rows"])
            
            workers = []
            total_sfs = 0
            total_only_now = 0
            total_sch = 0
            scam_workers = []
            
            for row in rows:
                # Имя работника
                name_elem = await row.query_selector(self.SELECTORS["worker_name"])
                name = await name_elem.inner_text() if name_elem else "Unknown"
                
                # SFS
                sfs_elem = await row.query_selector(self.SELECTORS["sfs_badge"])
                sfs = int(await sfs_elem.inner_text()) if sfs_elem else 0
                total_sfs += sfs
                
                # ONLY NOW
                only_now_elem = await row.query_selector(self.SELECTORS["only_now_badge"])
                only_now = int(await only_now_elem.inner_text()) if only_now_elem else 0
                total_only_now += only_now
                
                # SCH
                sch_elem = await row.query_selector(self.SELECTORS["sch_badge"])
                sch = int(await sch_elem.inner_text()) if sch_elem else 0
                total_sch += sch
                
                # Проверяем скам
                scam_red = await row.query_selector(self.SELECTORS["scam_icon_red"])
                scam_yellow = await row.query_selector(self.SELECTORS["scam_icon_yellow"])
                
                if scam_red or scam_yellow:
                    scam_workers.append(name)
                
                workers.append({
                    "name": name,
                    "sfs": sfs,
                    "only_now": only_now,
                    "sch": sch,
                    "has_scam": bool(scam_red or scam_yellow)
                })
            
            return {
                "success": True,
                "date": report_date or datetime.now().strftime("%Y-%m-%d"),
                "team": team or "all",
                "workers": workers,
                "totals": {
                    "sfs": total_sfs,
                    "only_now": total_only_now,
                    "sch": total_sch
                },
                "scam_workers": scam_workers,
                "workers_count": len(workers)
            }
        
        except Exception as e:
            logger.error(f"❌ _get_stats error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_worker_details(self, worker_name: str) -> Dict[str, Any]:
        """
        Получает детальную информацию о работнике
        
        Args:
            worker_name: Имя работника
        
        Returns:
            Детали работника
        """
        # TODO: Реализовать детальный парсинг работника
        return {
            "success": False,
            "error": "Not implemented yet"
        }
    
    async def _get_daily_report(self, report_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает дневной отчет
        
        Args:
            report_date: Дата отчета
        
        Returns:
            Дневной отчет
        """
        return await self._get_stats(report_date=report_date)

