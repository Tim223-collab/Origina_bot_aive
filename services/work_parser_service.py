"""
Сервис парсинга рабочего сайта с отчетами работников
Использует Playwright для веб-скрапинга
"""
import asyncio
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

import config

logger = logging.getLogger(__name__)


class WorkParserService:
    """Сервис для парсинга отчетов работников с веб-панели"""
    
    def __init__(self):
        self.base_url = config.WORK_SITE_URL or "http://91.228.153.202:8000"
        self.username = config.WORK_SITE_USERNAME or "Timofey"
        self.password = config.WORK_SITE_PASSWORD or "admin123"
        self.browser: Optional[Browser] = None
        self.screenshots_dir = config.DATA_DIR / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
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
    
    async def _init_browser(self):
        """Инициализация браузера Playwright"""
        if not self.browser:
            playwright = await async_playwright().start()
            # Для Linux сервера - используем chromium в headless режиме
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu'
                ]
            )
            logger.info("✅ Playwright браузер запущен (headless mode)")
    
    async def _close_browser(self):
        """Закрытие браузера"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            logger.info("🔒 Playwright браузер закрыт")
    
    async def _login(self, page: Page) -> bool:
        """Авторизация на сайте"""
        try:
            login_url = f"{self.base_url}/auth/login"
            logger.info(f"🔐 Переход на страницу авторизации: {login_url}")
            
            await page.goto(login_url, wait_until="networkidle")
            
            # Заполняем форму
            await page.fill(self.SELECTORS["login_username"], self.username)
            await page.fill(self.SELECTORS["login_password"], self.password)
            
            # Нажимаем войти
            await page.click(self.SELECTORS["login_submit"])
            
            # Ждем редиректа (успешный вход)
            await page.wait_for_url("**/admin/**", timeout=10000)
            
            logger.info("✅ Авторизация успешна")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    async def _wait_for_reports_load(self, page: Page):
        """Ожидание загрузки таблицы с отчетами"""
        try:
            # Ждем появления таблицы
            await page.wait_for_selector(self.SELECTORS["table_rows"], timeout=15000)
            
            # Дополнительно ждем пока завершится проверка blacklist (иконки загрузятся)
            await asyncio.sleep(3)
            
            logger.info("✅ Таблица отчетов загружена")
            
        except PlaywrightTimeout:
            logger.warning("⚠️ Таймаут при загрузке таблицы (возможно нет данных)")
    
    async def parse_reports(
        self,
        team: str = "Good Bunny",
        report_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Парсинг отчетов работников
        
        Args:
            team: Название команды ("Good Bunny", "Velvet", или "all")
            report_date: Дата в формате YYYY-MM-DD (по умолчанию - сегодня)
        
        Returns:
            Словарь с данными отчетов
        """
        try:
            await self._init_browser()
            
            # Создаем новую страницу
            page = await self.browser.new_page()
            
            # Авторизация
            if not await self._login(page):
                return {"success": False, "error": "Ошибка авторизации"}
            
            # Переход в "Проверка особо"
            reports_url = f"{self.base_url}/admin/reports"
            logger.info(f"📊 Переход на страницу отчетов: {reports_url}")
            await page.goto(reports_url, wait_until="networkidle")
            
            # Установка фильтров
            if not report_date:
                report_date = date.today().strftime("%Y-%m-%d")
            
            # Устанавливаем дату через evaluate (для input type="date" нужно устанавливать value)
            try:
                await page.evaluate(f"""
                    const dateInput = document.querySelector('{self.SELECTORS["date_filter"]}');
                    if (dateInput) {{
                        dateInput.value = '{report_date}';
                        dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """)
                logger.info(f"📅 Установлена дата: {report_date}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка установки даты: {e}")
            
            # Выбор команды (кнопки фильтра)
            team_map = {
                "Good Bunny": "team_good_bunny",
                "good bunny": "team_good_bunny",
                "goodbunny": "team_good_bunny",
                "Velvet": "team_velvet",
                "velvet": "team_velvet",
            }
            
            team_selector = team_map.get(team.strip())
            if team_selector:
                await page.click(self.SELECTORS[team_selector])
                logger.info(f"✅ Выбрана команда: {team}")
            else:
                logger.info("ℹ️ Показываем все команды")
            
            # Нажимаем кнопку "Применить фильтр" для отправки формы
            try:
                submit_btn = await page.query_selector('button[type="submit"]')
                if submit_btn:
                    await submit_btn.click()
                    logger.info("✅ Форма фильтров отправлена")
                    # Ждем навигации после submit
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка отправки формы: {e}")
            
            # Ждем загрузки таблицы
            await self._wait_for_reports_load(page)
            
            # Парсинг строк таблицы
            rows = await page.query_selector_all(self.SELECTORS["table_rows"])
            
            if not rows:
                logger.warning("⚠️ Таблица пуста (нет отчетов за выбранную дату)")
                await page.close()
                return {
                    "success": True,
                    "date": report_date,
                    "team": team,
                    "workers_count": 0,
                    "workers": [],
                    "total_sfs": 0,
                    "total_sch": 0,
                    "scam_detected": 0
                }
            
            logger.info(f"📋 Найдено строк в таблице: {len(rows)}")
            
            workers = []
            total_sfs = 0
            total_sch = 0
            scam_count = 0
            
            # Парсинг каждой строки
            for idx, row in enumerate(rows, 1):
                try:
                    worker_data = await self._parse_worker_row(row, page)
                    if worker_data:
                        workers.append(worker_data)
                        total_sfs += worker_data.get("sfs", 0)
                        total_sch += worker_data.get("sch", 0)
                        
                        if worker_data.get("has_scam"):
                            scam_count += 1
                        
                        logger.info(f"✅ [{idx}/{len(rows)}] Спарсен работник: {worker_data['name']}")
                
                except Exception as e:
                    logger.error(f"❌ Ошибка парсинга строки {idx}: {e}")
                    continue
            
            await page.close()
            
            result = {
                "success": True,
                "date": report_date,
                "team": team,
                "workers_count": len(workers),
                "workers": workers,
                "total_sfs": total_sfs,
                "total_sch": total_sch,
                "total_only_now": total_sfs - total_sch,
                "scam_detected": scam_count,
                "parsed_at": datetime.now().isoformat()
            }
            
            logger.info(f"🎉 Парсинг завершен! Работников: {len(workers)}, SFS: {total_sfs}, SCH: {total_sch}, Скам: {scam_count}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка парсинга: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            await self._close_browser()
    
    async def _parse_worker_row(self, row, page: Page) -> Optional[Dict[str, Any]]:
        """Парсинг одной строки таблицы (данные работника)"""
        try:
            # Имя работника
            name_elem = await row.query_selector(self.SELECTORS["worker_name"])
            name = await name_elem.inner_text() if name_elem else "Unknown"
            
            # Username (может отсутствовать)
            username_elem = await row.query_selector(self.SELECTORS["worker_username"])
            username = await username_elem.inner_text() if username_elem else None
            if username:
                username = username.strip().lstrip("@")
            
            # Команда
            team_elem = await row.query_selector(self.SELECTORS["team_badge"])
            team = await team_elem.inner_text() if team_elem else "Unknown"
            
            # ID отчета
            id_elem = await row.query_selector(self.SELECTORS["report_id"])
            report_id_text = await id_elem.inner_text() if id_elem else "#0"
            report_id = int(report_id_text.strip("#"))
            
            # SFS
            sfs_elem = await row.query_selector(self.SELECTORS["sfs_badge"])
            sfs = int(await sfs_elem.inner_text()) if sfs_elem else 0
            
            # SCH
            sch_elem = await row.query_selector(self.SELECTORS["sch_badge"])
            sch = int(await sch_elem.inner_text()) if sch_elem else 0
            
            # Only Now
            only_now_elem = await row.query_selector(self.SELECTORS["only_now_badge"])
            only_now = int(await only_now_elem.inner_text()) if only_now_elem else (sfs - sch)
            
            # Проверка скама
            scam_icon_red = await row.query_selector(self.SELECTORS["scam_icon_red"])
            scam_icon_yellow = await row.query_selector(self.SELECTORS["scam_icon_yellow"])
            scam_icon_green = await row.query_selector(self.SELECTORS["scam_icon_green"])
            
            has_scam = False
            scam_status = "clean"
            
            # Скам = только красный крестик (работник нашел скам-ассистентов)
            # Желтый треугольник = подозрительная активность (НЕ скам!)
            if scam_icon_red:
                has_scam = True
                scam_status = "scam_detected"
            elif scam_icon_yellow:
                has_scam = False  # Это не скам, это подозрительная активность
                scam_status = "suspicious"
            elif scam_icon_green:
                scam_status = "clean"
            
            worker_data = {
                "report_id": report_id,
                "name": name,
                "username": username,
                "team": team,
                "sfs": sfs,
                "sch": sch,
                "only_now": only_now,
                "has_scam": has_scam,
                "scam_status": scam_status
            }
            
            # Если есть скам - парсим детали
            if has_scam:
                scam_details_btn = await row.query_selector(self.SELECTORS["scam_details_btn"])
                if scam_details_btn:
                    worker_data["scam_details"] = await self._parse_scam_details(
                        scam_details_btn, page, report_id, name
                    )
            
            return worker_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга строки работника: {e}")
            return None
    
    async def _parse_scam_details(
        self, 
        button, 
        page: Page, 
        report_id: int,
        worker_name: str
    ) -> Dict[str, Any]:
        """
        Парсинг деталей скама (модальное окно)
        """
        try:
            # Кликаем на кнопку деталей
            await button.click()
            
            # Ждем появления модального окна
            await page.wait_for_selector(self.SELECTORS["modal"], timeout=5000)
            
            # Даем время на загрузку содержимого
            await asyncio.sleep(1)
            
            # Уменьшаем масштаб модального окна для большего количества данных
            await page.evaluate("""
                const modal = document.querySelector('#blacklistModalDynamic .modal-dialog');
                if (modal) {
                    modal.style.transform = 'scale(0.75)';
                    modal.style.transformOrigin = 'top center';
                }
            """)
            await asyncio.sleep(0.5)
            
            # Парсим содержимое модального окна
            modal_body = await page.query_selector(self.SELECTORS["modal_body"])
            
            if modal_body:
                modal_text = await modal_body.inner_text()
                modal_html = await modal_body.inner_html()
                
                # Создаем скриншот модального окна
                screenshot_path = await self._take_screenshot_modal(
                    page, 
                    f"scam_{report_id}_{worker_name}"
                )
                
                details = {
                    "text": modal_text,
                    "html": modal_html,
                    "screenshot": screenshot_path
                }
            else:
                details = {"error": "Не удалось загрузить детали"}
            
            # Закрываем модальное окно
            close_btn = await page.query_selector(self.SELECTORS["modal_close"])
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(0.5)
            
            return details
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга деталей скама: {e}")
            return {"error": str(e)}
    
    async def _take_screenshot(
        self, 
        page: Page, 
        name: str
    ) -> Optional[str]:
        """Создание скриншота всей страницы"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            
            logger.info(f"📸 Скриншот сохранен: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания скриншота: {e}")
            return None
    
    async def _take_screenshot_modal(
        self, 
        page: Page, 
        name: str
    ) -> Optional[str]:
        """Создание скриншота модального окна (с автопрокруткой)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            # Получаем элемент модального окна
            modal = await page.query_selector(self.SELECTORS["modal"])
            
            if modal:
                # Делаем скриншот только модального окна
                await modal.screenshot(path=str(filepath))
                logger.info(f"📸 Скриншот модального окна сохранен: {filepath}")
            else:
                # Fallback: скриншот всей страницы
                await page.screenshot(path=str(filepath), full_page=True)
                logger.info(f"📸 Скриншот (full page) сохранен: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания скриншота модального окна: {e}")
            # Fallback: пытаемся сделать обычный скриншот
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}_fallback.png"
                filepath = self.screenshots_dir / filename
                await page.screenshot(path=str(filepath))
                return str(filepath)
            except:
                return None
    
    async def get_worker_scam_screenshots(
        self, 
        worker_name: str, 
        team: str = "Good Bunny",
        report_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить скриншоты скама для конкретного работника
        (для запросов типа "покажи что со скамом у Алексея")
        """
        try:
            # Сначала парсим отчеты
            reports = await self.parse_reports(team=team, report_date=report_date)
            
            if not reports["success"]:
                return reports
            
            # Ищем работника
            worker = None
            for w in reports["workers"]:
                if worker_name.lower() in w["name"].lower():
                    worker = w
                    break
            
            if not worker:
                return {
                    "success": False,
                    "error": f"Работник '{worker_name}' не найден в отчетах"
                }
            
            if not worker.get("has_scam"):
                return {
                    "success": True,
                    "worker": worker,
                    "message": f"У работника {worker['name']} нет скама ✅"
                }
            
            return {
                "success": True,
                "worker": worker,
                "scam_details": worker.get("scam_details"),
                "message": f"Найден скам у работника {worker['name']} 🚨"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения скриншотов скама: {e}")
            return {"success": False, "error": str(e)}


# Глобальный экземпляр сервиса
_parser_service = None

def get_parser_service() -> WorkParserService:
    """Получить глобальный экземпляр парсера"""
    global _parser_service
    if _parser_service is None:
        _parser_service = WorkParserService()
    return _parser_service

