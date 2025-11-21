"""
Базовый класс для всех парсеров

Определяет общий интерфейс и базовую функциональность
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page
from pathlib import Path
import logging
import config


logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Базовый класс для парсера
    
    Все конкретные парсеры должны наследоваться от этого класса
    и реализовать абстрактные методы
    """
    
    # Метаданные парсера (переопределяются в дочерних классах)
    NAME: str = "base"
    DESCRIPTION: str = "Базовый парсер"
    VERSION: str = "1.0.0"
    SUPPORTED_OPERATIONS: List[str] = []
    
    def __init__(self, config_data: Dict[str, Any] = None):
        """
        Инициализация парсера
        
        Args:
            config_data: Конфигурация парсера (URL, credentials, etc.)
        """
        self.config_data = config_data or {}
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.screenshots_dir = config.DATA_DIR / "screenshots" / self.NAME
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔧 {self.NAME} parser initialized")
    
    async def initialize(self) -> bool:
        """
        Инициализирует браузер и подготавливает парсер к работе
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            if not self.browser:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                self.page = await self.browser.new_page()
                logger.info(f"✅ {self.NAME} browser initialized")
                return True
        except Exception as e:
            logger.error(f"❌ {self.NAME} initialization error: {e}")
            return False
        
        return True
    
    async def close(self):
        """Закрывает браузер и освобождает ресурсы"""
        if self.page:
            await self.page.close()
            self.page = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        logger.info(f"🔒 {self.NAME} browser closed")
    
    @abstractmethod
    async def login(self) -> bool:
        """
        Авторизация на сайте
        
        Returns:
            True если успешно, False если ошибка
        """
        pass
    
    @abstractmethod
    async def parse(self, **kwargs) -> Dict[str, Any]:
        """
        Основной метод парсинга
        
        Args:
            **kwargs: Параметры парсинга (зависят от конкретного парсера)
        
        Returns:
            Словарь с результатами парсинга
        """
        pass
    
    async def take_screenshot(self, name: str) -> Optional[Path]:
        """
        Делает скриншот текущей страницы
        
        Args:
            name: Имя файла (без расширения)
        
        Returns:
            Путь к скриншоту или None
        """
        if not self.page:
            return None
        
        try:
            screenshot_path = self.screenshots_dir / f"{name}.png"
            await self.page.screenshot(path=str(screenshot_path))
            logger.info(f"📸 Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"❌ Screenshot error: {e}")
            return None
    
    def get_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о парсере
        
        Returns:
            Словарь с метаданными
        """
        return {
            "name": self.NAME,
            "description": self.DESCRIPTION,
            "version": self.VERSION,
            "supported_operations": self.SUPPORTED_OPERATIONS
        }
    
    async def validate_config(self) -> bool:
        """
        Проверяет валидность конфигурации
        
        Returns:
            True если конфиг валиден
        """
        # Базовая реализация - переопределяется в дочерних классах
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Проверяет работоспособность парсера
        
        Returns:
            Словарь со статусом и деталями
        """
        status = {
            "parser": self.NAME,
            "browser_initialized": self.browser is not None,
            "page_ready": self.page is not None,
            "config_valid": await self.validate_config(),
            "healthy": False
        }
        
        status["healthy"] = all([
            status["browser_initialized"],
            status["page_ready"],
            status["config_valid"]
        ])
        
        return status

