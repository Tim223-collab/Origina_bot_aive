"""
Универсальная система парсинга для разных сайтов

Архитектура:
- BaseParser - базовый класс для всех парсеров
- Конкретные парсеры наследуются от BaseParser
- ParserFactory - фабрика для создания парсеров
- ParserRegistry - реестр доступных парсеров
"""
from .base_parser import BaseParser
from .work_site_parser import WorkSiteParser
from .parser_factory import ParserFactory, ParserRegistry

__all__ = [
    "BaseParser",
    "WorkSiteParser",
    "ParserFactory",
    "ParserRegistry"
]

