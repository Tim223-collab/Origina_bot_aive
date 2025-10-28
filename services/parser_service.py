"""
Сервис парсинга рабочего сайта через Playwright
"""
from playwright.async_api import async_playwright, Browser, Page
from typing import Dict, List, Optional
import asyncio
import config


class WorkSiteParser:
    """
    Парсер админ-панели для получения статистики работников
    """
    
    def __init__(self):
        self.url = config.WORK_SITE_URL
        self.username = config.WORK_SITE_USERNAME
        self.password = config.WORK_SITE_PASSWORD
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
    
    async def start(self):
        """Запускает браузер"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
    
    async def close(self):
        """Закрывает браузер"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def login(self) -> bool:
        """
        Логинится на сайт
        
        Returns:
            True если успешно залогинился
        """
        if not self.page:
            await self.start()
        
        try:
            await self.page.goto(self.url, wait_until="networkidle")
            
            # Ждем форму логина (нужно будет адаптировать под реальный сайт)
            # Это примерная логика - нужно будет посмотреть реальные селекторы
            
            # Пытаемся найти поля логина
            username_input = await self.page.query_selector('input[type="text"], input[name*="user"], input[name*="login"]')
            password_input = await self.page.query_selector('input[type="password"]')
            
            if username_input and password_input:
                await username_input.fill(self.username)
                await password_input.fill(self.password)
                
                # Ищем кнопку входа
                submit_button = await self.page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    await self.page.wait_for_load_state("networkidle")
                    
                    self.is_logged_in = True
                    return True
            
            # Если уже залогинены (есть cookies)
            if "Админ панель" in await self.page.content():
                self.is_logged_in = True
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Ошибка логина: {e}")
            return False
    
    async def parse_statistics(self, date: str = None) -> Optional[Dict]:
        """
        Парсит статистику со страницы
        
        Args:
            date: Дата в формате DD.MM.YYYY (если нужно)
            
        Returns:
            Словарь со статистикой
        """
        if not self.is_logged_in:
            if not await self.login():
                return None
        
        try:
            # Устанавливаем дату если нужно
            if date:
                date_input = await self.page.query_selector('input[type="date"]')
                if date_input:
                    # Конвертируем формат даты DD.MM.YYYY -> YYYY-MM-DD
                    parts = date.split('.')
                    if len(parts) == 3:
                        iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        await date_input.fill(iso_date)
                        
                        # Применяем фильтр
                        apply_button = await self.page.query_selector('button:has-text("Применить")')
                        if apply_button:
                            await apply_button.click()
                            await self.page.wait_for_load_state("networkidle")
            
            # Парсим карточки статистики (синие, зеленые, голубые, желтые блоки)
            stats = {
                "total_records": 0,
                "total_sfs": 0,
                "total_sch": 0,
                "active_users": 0,
                "workers": []
            }
            
            # Парсим верхние карточки
            cards = await self.page.query_selector_all('div[class*="card"], div[class*="stat"]')
            for card in cards[:4]:  # Первые 4 карточки
                text = await card.inner_text()
                if "записей" in text.lower():
                    stats["total_records"] = self._extract_number(text)
                elif "sfs" in text.lower():
                    stats["total_sfs"] = self._extract_number(text)
                elif "sch" in text.lower():
                    stats["total_sch"] = self._extract_number(text)
                elif "сотрудник" in text.lower():
                    stats["active_users"] = self._extract_number(text)
            
            # Парсим таблицу работников
            table_rows = await self.page.query_selector_all('table tbody tr')
            
            for row in table_rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 6:
                    worker_data = {}
                    
                    # Имя сотрудника
                    name_cell = cells[0]
                    name_text = await name_cell.inner_text()
                    lines = name_text.strip().split('\n')
                    worker_data['name'] = lines[0] if lines else "Unknown"
                    worker_data['username'] = lines[1] if len(lines) > 1 else ""
                    
                    # Команда
                    team_cell = cells[1]
                    team_text = await team_cell.inner_text()
                    worker_data['team'] = team_text.strip()
                    
                    # Дата отчета
                    date_cell = cells[2]
                    date_text = await date_cell.inner_text()
                    worker_data['date'] = date_text.strip()
                    
                    # SFS
                    sfs_cell = cells[4] if len(cells) > 4 else None
                    if sfs_cell:
                        sfs_text = await sfs_cell.inner_text()
                        worker_data['sfs'] = self._extract_number(sfs_text)
                    
                    # Only now
                    only_now_cell = cells[5] if len(cells) > 5 else None
                    if only_now_cell:
                        only_now_text = await only_now_cell.inner_text()
                        worker_data['only_now'] = self._extract_number(only_now_text)
                    
                    # SCH
                    sch_cell = cells[6] if len(cells) > 6 else None
                    if sch_cell:
                        sch_text = await sch_cell.inner_text()
                        worker_data['sch'] = self._extract_number(sch_text)
                    
                    stats['workers'].append(worker_data)
            
            return stats
            
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_number(self, text: str) -> int:
        """Извлекает число из текста"""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else 0
    
    async def get_quick_summary(self) -> Optional[str]:
        """
        Получает краткую сводку
        
        Returns:
            Текстовая сводка для отправки пользователю
        """
        stats = await self.parse_statistics()
        if not stats:
            return None
        
        summary = f"""📊 **Статистика на сегодня**

📝 Всего записей: {stats['total_records']}
✅ Успешных (SFS): {stats['total_sfs']}
📋 Проверено (SCH): {stats['total_sch']}
👥 Активных сотрудников: {len(stats['workers'])}

**Топ работников:**
"""
        
        # Сортируем по SFS
        top_workers = sorted(stats['workers'], 
                           key=lambda x: x.get('sfs', 0), 
                           reverse=True)[:5]
        
        for i, worker in enumerate(top_workers, 1):
            summary += f"{i}. {worker['name']} - {worker.get('sfs', 0)} SFS\n"
        
        return summary
    
    async def __aenter__(self):
        """Context manager support"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        await self.close()

