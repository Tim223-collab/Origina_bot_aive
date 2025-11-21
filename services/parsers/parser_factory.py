"""
Фабрика и реестр парсеров

Управляет созданием и регистрацией парсеров
"""
from typing import Dict, Type, Optional, List
from .base_parser import BaseParser
from .work_site_parser import WorkSiteParser
import logging


logger = logging.getLogger(__name__)


class ParserRegistry:
    """
    Реестр доступных парсеров
    """
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    
    @classmethod
    def register(cls, parser_class: Type[BaseParser]):
        """
        Регистрирует парсер
        
        Args:
            parser_class: Класс парсера
        """
        name = parser_class.NAME
        cls._parsers[name] = parser_class
        logger.info(f"✅ Parser registered: {name}")
    
    @classmethod
    def get_parser_class(cls, name: str) -> Optional[Type[BaseParser]]:
        """
        Получает класс парсера по имени
        
        Args:
            name: Имя парсера
        
        Returns:
            Класс парсера или None
        """
        return cls._parsers.get(name)
    
    @classmethod
    def list_parsers(cls) -> List[Dict[str, str]]:
        """
        Возвращает список доступных парсеров
        
        Returns:
            Список словарей с информацией о парсерах
        """
        return [
            {
                "name": parser_class.NAME,
                "description": parser_class.DESCRIPTION,
                "version": parser_class.VERSION,
                "operations": parser_class.SUPPORTED_OPERATIONS
            }
            for parser_class in cls._parsers.values()
        ]
    
    @classmethod
    def unregister(cls, name: str):
        """Удаляет парсер из реестра"""
        if name in cls._parsers:
            del cls._parsers[name]
            logger.info(f"🗑️ Parser unregistered: {name}")


class ParserFactory:
    """
    Фабрика для создания парсеров
    """
    
    @staticmethod
    async def create_parser(
        name: str,
        config_data: Dict = None,
        auto_init: bool = True
    ) -> Optional[BaseParser]:
        """
        Создает и инициализирует парсер
        
        Args:
            name: Имя парсера
            config_data: Конфигурация парсера
            auto_init: Автоматически инициализировать браузер
        
        Returns:
            Экземпляр парсера или None
        """
        parser_class = ParserRegistry.get_parser_class(name)
        
        if not parser_class:
            logger.error(f"❌ Parser not found: {name}")
            return None
        
        try:
            parser = parser_class(config_data)
            
            if auto_init:
                success = await parser.initialize()
                if not success:
                    logger.error(f"❌ Parser initialization failed: {name}")
                    return None
            
            logger.info(f"✅ Parser created: {name}")
            return parser
        
        except Exception as e:
            logger.error(f"❌ Parser creation error: {name}, {e}")
            return None
    
    @staticmethod
    def list_available_parsers() -> List[Dict[str, str]]:
        """
        Возвращает список доступных парсеров
        
        Returns:
            Список парсеров с информацией
        """
        return ParserRegistry.list_parsers()


# Регистрация встроенных парсеров
ParserRegistry.register(WorkSiteParser)

# Импортируем и регистрируем ДТЕК парсер
try:
    from .dtek_parser import DTEKParser
    ParserRegistry.register(DTEKParser)
    logger.info("✅ DTEK Parser registered")
except ImportError as e:
    logger.warning(f"⚠️ DTEK Parser not imported: {e}")


# Пример добавления шаблона для нового парсера
class ExampleParser(BaseParser):
    """
    Пример парсера для другого сайта
    
    Для добавления нового парсера:
    1. Наследуйтесь от BaseParser
    2. Определите NAME, DESCRIPTION, VERSION, SUPPORTED_OPERATIONS
    3. Реализуйте login() и parse()
    4. Зарегистрируйте через ParserRegistry.register()
    """
    
    NAME = "example"
    DESCRIPTION = "Пример парсера"
    VERSION = "1.0.0"
    SUPPORTED_OPERATIONS = ["parse_data"]
    
    async def login(self) -> bool:
        """Реализация авторизации"""
        # Ваш код авторизации здесь
        return True
    
    async def parse(self, **kwargs) -> Dict:
        """Реализация парсинга"""
        # Ваш код парсинга здесь
        return {
            "success": True,
            "data": {}
        }


# Не регистрируем ExampleParser, это просто пример
# ParserRegistry.register(ExampleParser)

