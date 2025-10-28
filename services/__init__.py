"""
Сервисы бота
"""
from .ai_service import AIService
from .memory_service import MemoryService
from .extras_service import ExtrasService
from .work_parser_service import WorkParserService

# Алиас для обратной совместимости
WorkSiteParser = WorkParserService

__all__ = ["AIService", "MemoryService", "ExtrasService", "WorkParserService", "WorkSiteParser"]

