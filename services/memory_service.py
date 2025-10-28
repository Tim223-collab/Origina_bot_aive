"""
Сервис управления памятью бота
"""
from typing import List, Dict, Any, Optional
from database import Database
from .ai_service import AIService


class MemoryService:
    """
    Управляет краткосрочной и долгосрочной памятью бота
    """
    
    def __init__(self, db: Database, ai_service: AIService):
        self.db = db
        self.ai = ai_service
    
    async def get_context_for_ai(self, user_id: int) -> str:
        """
        Формирует контекст для ИИ на основе долгосрочной памяти
        
        Returns:
            Строка с важной информацией о пользователе
        """
        memories = await self.db.recall(user_id)
        
        if not memories:
            return ""
        
        # Группируем факты по категориям
        context_parts = []
        current_category = None
        category_facts = []
        
        for mem in memories:
            if mem['category'] != current_category:
                if category_facts:
                    category_name = current_category.replace("_", " ").title()
                    context_parts.append(f"{category_name}: {', '.join(category_facts)}")
                current_category = mem['category']
                category_facts = []
            
            category_facts.append(f"{mem['key']} - {mem['value']}")
        
        # Добавляем последнюю категорию
        if category_facts:
            category_name = current_category.replace("_", " ").title()
            context_parts.append(f"{category_name}: {', '.join(category_facts)}")
        
        if context_parts:
            return "\n\nЧто я знаю о пользователе:\n" + "\n".join(context_parts)
        
        return ""
    
    async def remember_fact(self, user_id: int, category: str, 
                           key: str, value: str) -> bool:
        """
        Сохраняет факт в долгосрочную память
        
        Args:
            user_id: ID пользователя
            category: Категория (personal, work, preferences, etc)
            key: Ключ факта
            value: Значение
        """
        try:
            await self.db.remember(user_id, category, key, value)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения в память: {e}")
            return False
    
    async def recall_facts(self, user_id: int, 
                          category: str = None) -> List[Dict[str, Any]]:
        """Получает факты из памяти"""
        return await self.db.recall(user_id, category)
    
    async def forget_fact(self, user_id: int, category: str, key: str) -> bool:
        """Удаляет факт из памяти"""
        try:
            await self.db.forget(user_id, category, key)
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления из памяти: {e}")
            return False
    
    async def auto_remember_from_conversation(self, user_id: int, 
                                             conversation_text: str) -> Optional[List[str]]:
        """
        Автоматически извлекает и сохраняет важные факты из разговора
        
        Returns:
            Список сохраненных фактов для отображения пользователю
        """
        # Используем ИИ для извлечения фактов
        facts_text = await self.ai.extract_facts(conversation_text)
        
        if not facts_text:
            return None
        
        # Простой парсинг фактов (можно улучшить)
        saved_facts = []
        lines = facts_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Пробуем извлечь структурированные данные
            # Формат: "Категория: ключ - значение"
            if ':' in line and '-' in line:
                try:
                    category_part, fact_part = line.split(':', 1)
                    category = category_part.strip().lower().replace(' ', '_')
                    
                    if '-' in fact_part:
                        key, value = fact_part.split('-', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        await self.remember_fact(user_id, category, key, value)
                        saved_facts.append(f"{category}: {key} = {value}")
                except:
                    continue
        
        return saved_facts if saved_facts else None
    
    async def format_memory_for_display(self, user_id: int, 
                                       category: str = None) -> str:
        """
        Форматирует память для отображения пользователю
        """
        memories = await self.recall_facts(user_id, category)
        
        if not memories:
            return "🧠 Память пуста"
        
        # Группируем по категориям
        categories = {}
        for mem in memories:
            cat = mem['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"  • {mem['key']}: {mem['value']}")
        
        # Форматируем вывод
        output = ["🧠 **Долгосрочная память**\n"]
        for cat, facts in categories.items():
            cat_name = cat.replace('_', ' ').title()
            output.append(f"**{cat_name}:**")
            output.extend(facts)
            output.append("")
        
        return "\n".join(output)

