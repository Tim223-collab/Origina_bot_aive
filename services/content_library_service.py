"""
Сервис умной библиотеки контента
Сохраняет и управляет всем контентом пользователя с AI категоризацией
"""
import re
import json
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from database import Database
from services import AIService
from services.vision_service import VisionService


class ContentLibraryService:
    """
    Умная библиотека контента с AI категоризацией
    
    Поддерживаемые типы контента:
    - image: Изображения (карты, скриншоты, фото)
    - text: Обычный текст
    - code: Код (Python, JS, и т.д.)
    - link: Ссылки (YouTube, статьи, видео)
    - document: Документы (PDF, DOCX и т.д.)
    - audio: Аудио файлы
    - video: Видео файлы
    
    Категории (AI определяет автоматически):
    - maps: Карты, схемы проезда
    - funny: Смешное (мемы, видео)
    - useful: Полезное (статьи, туториалы)
    - work: Рабочее
    - personal: Личное
    - code: Код и программирование
    - docs: Документация
    - reference: Справочная информация
    """
    
    # Категории контента
    CATEGORIES = {
        "maps": "🗺️ Карты и схемы",
        "funny": "😂 Смешное",
        "useful": "💡 Полезное",
        "work": "💼 Работа",
        "personal": "👤 Личное",
        "code": "💻 Код",
        "docs": "📚 Документация",
        "reference": "📖 Справочник",
        "media": "🎬 Медиа",
        "other": "📂 Другое"
    }
    
    # Расширения файлов для определения типа
    CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', 
                      '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.sql', '.sh', '.bash'}
    
    def __init__(self, db: Database, ai: AIService, vision: VisionService):
        self.db = db
        self.ai = ai
        self.vision = vision
        
    async def analyze_and_save(
        self,
        user_id: int,
        content_type: str,
        **kwargs
    ) -> Tuple[int, Dict]:
        """
        Анализирует контент через AI и сохраняет в библиотеку
        
        Args:
            user_id: ID пользователя
            content_type: Тип контента
            **kwargs: Параметры контента (file_id, url, text_content и т.д.)
            
        Returns:
            (content_id, ai_analysis) - ID записи и результат AI анализа
        """
        # Анализируем контент через AI
        analysis = await self._analyze_content(content_type, **kwargs)
        
        # Сохраняем в БД
        content_id = await self.db.save_content(
            user_id=user_id,
            content_type=content_type,
            description=analysis.get('description'),
            category=analysis.get('category'),
            **kwargs
        )
        
        return content_id, analysis
    
    async def _analyze_content(
        self,
        content_type: str,
        file_id: str = None,
        url: str = None,
        text_content: str = None,
        image_bytes: bytes = None,
        file_name: str = None,
        **kwargs
    ) -> Dict:
        """
        Анализирует контент через AI для определения категории и описания
        
        Returns:
            {
                "description": "Описание контента",
                "category": "maps|funny|useful|...",
                "suggested_title": "Предложенное название",
                "tags": ["тег1", "тег2"]
            }
        """
        
        # === ИЗОБРАЖЕНИЯ ===
        if content_type == "image" and image_bytes:
            # Используем Gemini для анализа изображения
            vision_result = await self.vision.analyze_image(
                image_bytes,
                prompt="Опиши что на изображении. Это карта? Мем? Скриншот? Фото?"
            )
            
            # AI категоризация на основе описания от Gemini
            return await self._categorize_by_description(vision_result, content_type)
        
        # === ТЕКСТ / КОД ===
        elif content_type in ["text", "code"] and text_content:
            # Определяем это код или обычный текст
            is_code = self._detect_code(text_content, file_name)
            actual_type = "code" if is_code else "text"
            
            # Анализируем через AI
            prompt = f"""Проанализируй этот {"код" if is_code else "текст"}:

{text_content[:500]}...

Определи:
1. Что это? (краткое описание)
2. Категория: maps, funny, useful, work, personal, code, docs, reference, media, other
3. Предложи название (2-5 слов)
4. Теги (2-4 ключевых слова)

Ответ в JSON:
{{
    "description": "краткое описание",
    "category": "категория",
    "suggested_title": "название",
    "tags": ["тег1", "тег2"]
}}"""

            messages = [
                {"role": "system", "content": "Ты эксперт по категоризации контента. Отвечай ТОЛЬКО JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.ai.chat(messages, temperature=0.3, max_tokens=200, json_mode=True)
            
            if response:
                try:
                    result = json.loads(response)
                    result['content_type'] = actual_type  # Уточняем тип
                    return result
                except:
                    pass
        
        # === ССЫЛКИ ===
        elif content_type == "link" and url:
            return await self._analyze_link(url)
        
        # === FALLBACK ===
        return {
            "description": f"Контент типа {content_type}",
            "category": "other",
            "suggested_title": "Без названия",
            "tags": []
        }
    
    async def _categorize_by_description(self, description: str, content_type: str) -> Dict:
        """Категоризирует контент на основе текстового описания"""
        
        prompt = f"""У нас есть {content_type} с описанием:

"{description}"

Определи:
1. Категорию: maps (карты), funny (смешное), useful (полезное), work (работа), personal (личное), code (код), docs (документация), reference (справочник), media (медиа), other (другое)
2. Предложи короткое название (2-5 слов)
3. Добавь 2-4 тега

Ответ в JSON:
{{
    "description": "{description[:100]}...",
    "category": "категория",
    "suggested_title": "название",
    "tags": ["тег1", "тег2"]
}}"""

        messages = [
            {"role": "system", "content": "Ты эксперт по категоризации. Отвечай ТОЛЬКО JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.ai.chat(messages, temperature=0.3, max_tokens=150, json_mode=True)
        
        if response:
            try:
                result = json.loads(response)
                result['description'] = description  # Сохраняем полное описание
                return result
            except:
                pass
        
        # Fallback
        return {
            "description": description,
            "category": "other",
            "suggested_title": "Без названия",
            "tags": []
        }
    
    async def _analyze_link(self, url: str) -> Dict:
        """Анализирует ссылку и определяет тип контента"""
        
        # Определяем тип ссылки по URL
        url_lower = url.lower()
        
        if any(domain in url_lower for domain in ['youtube.com', 'youtu.be', 'vimeo.com']):
            category = "media"
            description = "Видео"
            suggested_title = "Видео с " + self._extract_domain(url)
        
        elif any(domain in url_lower for domain in ['github.com', 'gitlab.com', 'stackoverflow.com']):
            category = "code"
            description = "Код / Программирование"
            suggested_title = "Ссылка на " + self._extract_domain(url)
        
        elif any(domain in url_lower for domain in ['wikipedia.org', 'docs.', 'documentation']):
            category = "docs"
            description = "Документация / Статья"
            suggested_title = "Документация"
        
        else:
            category = "reference"
            description = f"Ссылка на {self._extract_domain(url)}"
            suggested_title = self._extract_domain(url)
        
        return {
            "description": description,
            "category": category,
            "suggested_title": suggested_title,
            "tags": [self._extract_domain(url)]
        }
    
    async def smart_search(self, user_id: int, query: str) -> List[Dict]:
        """
        Умный поиск по библиотеке контента с AI пониманием
        
        Args:
            user_id: ID пользователя
            query: Запрос на естественном языке ("дай карту метро", "покажи смешные видео")
            
        Returns:
            Список найденного контента
        """
        # AI понимает что ищет пользователь
        search_params = await self._parse_search_query(query)
        
        # Ищем в БД
        results = await self.db.get_content(
            user_id=user_id,
            content_type=search_params.get('content_type'),
            category=search_params.get('category'),
            search=search_params.get('keywords'),
            limit=search_params.get('limit', 20)
        )
        
        return results
    
    async def _parse_search_query(self, query: str) -> Dict:
        """
        Парсит поисковый запрос через AI
        
        Returns:
            {
                "content_type": "image|text|code|link|...",
                "category": "maps|funny|...",
                "keywords": "ключевые слова для поиска",
                "limit": 10
            }
        """
        
        prompt = f"""Пользователь ищет в своей библиотеке контента:

"{query}"

Определи параметры поиска:
- content_type: image, text, code, link, video, document (или null если не важно)
- category: maps, funny, useful, work, personal, code, docs, reference, media, other (или null)
- keywords: ключевые слова для поиска по названию/описанию
- limit: сколько результатов показать (10-50)

Примеры:
- "дай карту метро" → {{"content_type": "image", "category": "maps", "keywords": "метро", "limit": 10}}
- "покажи смешные видео" → {{"content_type": "link", "category": "funny", "keywords": "видео", "limit": 20}}
- "найди код по API" → {{"content_type": "code", "category": null, "keywords": "API", "limit": 10}}

Ответ JSON:
{{
    "content_type": null_или_тип,
    "category": null_или_категория,
    "keywords": "ключевые слова",
    "limit": число
}}"""

        messages = [
            {"role": "system", "content": "Ты парсишь поисковые запросы. Отвечай ТОЛЬКО JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.ai.chat(messages, temperature=0.2, max_tokens=100, json_mode=True)
        
        if response:
            try:
                return json.loads(response)
            except:
                pass
        
        # Fallback - простой поиск по ключевым словам
        return {
            "content_type": None,
            "category": None,
            "keywords": query,
            "limit": 20
        }
    
    def _detect_code(self, text: str, file_name: str = None) -> bool:
        """Определяет является ли текст кодом"""
        
        # Проверяем расширение файла
        if file_name:
            ext = Path(file_name).suffix.lower()
            if ext in self.CODE_EXTENSIONS:
                return True
        
        # Проверяем наличие кодовых паттернов
        code_patterns = [
            r'def\s+\w+\s*\(',  # Python functions
            r'function\s+\w+\s*\(',  # JS functions
            r'class\s+\w+',  # Classes
            r'import\s+\w+',  # Imports
            r'from\s+\w+\s+import',  # Python imports
            r'#include\s*<',  # C/C++ includes
            r'package\s+\w+',  # Java/Go packages
            r'=>',  # Arrow functions
            r'\{\s*\n\s*\w+:',  # JSON/objects
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _extract_domain(self, url: str) -> str:
        """Извлекает домен из URL"""
        import re
        match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url)
        if match:
            domain = match.group(1)
            # Убираем .com, .org и т.д. для красоты
            return domain.split('.')[0].title()
        return "Ссылка"
    
    async def get_library_stats(self, user_id: int) -> str:
        """
        Получает красивую статистику библиотеки
        
        Returns:
            Форматированная строка со статистикой
        """
        stats = await self.db.get_content_stats(user_id)
        categories = await self.db.get_categories(user_id)
        
        if not stats:
            return "📚 <b>Библиотека пуста</b>\n\nОтправь мне что-нибудь для сохранения!"
        
        # Иконки для типов контента
        type_icons = {
            "image": "🖼️",
            "text": "📝",
            "code": "💻",
            "link": "🔗",
            "video": "🎬",
            "document": "📄",
            "audio": "🎵"
        }
        
        total = sum(stats.values())
        
        result = f"📚 <b>Твоя библиотека</b>\n\n"
        result += f"📊 <b>Всего элементов:</b> {total}\n\n"
        
        result += "<b>По типам:</b>\n"
        for content_type, count in sorted(stats.items(), key=lambda x: -x[1]):
            icon = type_icons.get(content_type, "📁")
            result += f"{icon} {content_type.title()}: {count}\n"
        
        if categories:
            result += f"\n<b>Категории:</b>\n"
            for cat in categories[:8]:  # Топ 8 категорий
                emoji = self.CATEGORIES.get(cat, "📂").split()[0]
                result += f"{emoji} {cat.title()} "
            if len(categories) > 8:
                result += f"\n+ еще {len(categories) - 8}"
        
        return result
    
    async def should_auto_save(
        self,
        content_type: str,
        text: str = None,
        caption: str = None,
        file_name: str = None
    ) -> Dict:
        """
        Умное определение - нужно ли сохранить контент автоматически
        
        Args:
            content_type: Тип контента (image, text, link, document)
            text: Текст сообщения
            caption: Подпись к медиа
            file_name: Имя файла
            
        Returns:
            {
                "should_save": bool,
                "reason": str,
                "confidence": float  # 0.0-1.0
            }
        """
        
        # Формируем контекст для AI
        context_parts = []
        
        if content_type == "image":
            if caption:
                context_parts.append(f"Изображение с подписью: '{caption}'")
            else:
                context_parts.append("Изображение без подписи")
        
        elif content_type == "document":
            context_parts.append(f"Документ: {file_name or 'без имени'}")
        
        elif content_type == "text":
            if text and len(text) < 50:
                return {"should_save": False, "reason": "Короткое сообщение", "confidence": 0.9}
            context_parts.append(f"Текст: '{text[:200]}'")
        
        elif content_type == "link":
            context_parts.append(f"Ссылка: {text}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""Пользователь отправил контент:

{context}

Определи: это важная информация которую стоит сохранить в библиотеку?

СОХРАНЯТЬ СТОИТ:
- Карты, схемы, инфографику
- Полезные ссылки (статьи, видео, туториалы)
- Код, сниппеты
- Длинный текст с информацией
- Документы
- Контакты, адреса
- Рецепты, инструкции

НЕ СОХРАНЯТЬ:
- Короткие реплики в диалоге
- Вопросы к боту
- Команды
- Мемы без контекста (если нет явного запроса)

Ответ JSON:
{{
    "should_save": true/false,
    "reason": "почему да/нет (кратко)",
    "confidence": 0.0-1.0
}}"""

        messages = [
            {"role": "system", "content": "Ты определяешь стоит ли сохранять контент. Отвечай ТОЛЬКО JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.ai.chat(messages, temperature=0.3, max_tokens=100, json_mode=True)
            
            if response:
                result = json.loads(response)
                return result
        except Exception as e:
            print(f"❌ Ошибка определения автосохранения: {e}")
        
        # Fallback - не сохраняем по умолчанию
        return {
            "should_save": False,
            "reason": "Не удалось определить",
            "confidence": 0.5
        }

