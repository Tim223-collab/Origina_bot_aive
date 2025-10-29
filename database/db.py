"""
Асинхронная работа с SQLite базой данных
"""
import aiosqlite
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .models import ALL_TABLES


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            for table_sql in ALL_TABLES:
                await db.execute(table_sql)
            await db.commit()
            
    async def ensure_user(self, user_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None):
        """Создает пользователя если его нет"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
            
            await db.execute("""
                UPDATE users 
                SET last_active = CURRENT_TIMESTAMP,
                    username = COALESCE(?, username),
                    first_name = COALESCE(?, first_name),
                    last_name = COALESCE(?, last_name)
                WHERE user_id = ?
            """, (username, first_name, last_name, user_id))
            
            await db.commit()
    
    # === CONVERSATIONS ===
    
    async def add_message(self, user_id: int, role: str, content: str):
        """Добавляет сообщение в историю"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO conversations (user_id, role, content)
                VALUES (?, ?, ?)
            """, (user_id, role, content))
            await db.commit()
    
    async def get_recent_messages(self, user_id: int, limit: int = 20) -> List[Dict[str, str]]:
        """Получает последние сообщения пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT role, content, timestamp
                FROM conversations
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in reversed(rows)]
    
    async def clear_conversation(self, user_id: int):
        """Очищает историю диалога"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            await db.commit()
    
    # === LONG TERM MEMORY ===
    
    async def remember(self, user_id: int, category: str, key: str, value: str):
        """Сохраняет факт в долгосрочную память"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO long_term_memory 
                (user_id, category, key, value, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, category, key, value))
            await db.commit()
    
    async def recall(self, user_id: int, category: str = None) -> List[Dict[str, Any]]:
        """Получает факты из памяти"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if category:
                query = """
                    SELECT category, key, value, created_at, updated_at
                    FROM long_term_memory
                    WHERE user_id = ? AND category = ?
                    ORDER BY updated_at DESC
                """
                params = (user_id, category)
            else:
                query = """
                    SELECT category, key, value, created_at, updated_at
                    FROM long_term_memory
                    WHERE user_id = ?
                    ORDER BY category, updated_at DESC
                """
                params = (user_id,)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def forget(self, user_id: int, category: str, key: str):
        """Удаляет факт из памяти"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM long_term_memory
                WHERE user_id = ? AND category = ? AND key = ?
            """, (user_id, category, key))
            await db.commit()
    
    # === NOTES ===
    
    async def add_note(self, user_id: int, content: str, title: str = None, 
                      tags: List[str] = None) -> int:
        """Добавляет заметку"""
        tags_str = json.dumps(tags) if tags else None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO notes (user_id, title, content, tags)
                VALUES (?, ?, ?, ?)
            """, (user_id, title, content, tags_str))
            await db.commit()
            return cursor.lastrowid
    
    async def get_notes(self, user_id: int, search: str = None) -> List[Dict[str, Any]]:
        """Получает заметки с опциональным поиском"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if search:
                query = """
                    SELECT id, title, content, tags, created_at
                    FROM notes
                    WHERE user_id = ? AND (
                        title LIKE ? OR content LIKE ? OR tags LIKE ?
                    )
                    ORDER BY created_at DESC
                """
                pattern = f"%{search}%"
                params = (user_id, pattern, pattern, pattern)
            else:
                query = """
                    SELECT id, title, content, tags, created_at
                    FROM notes
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """
                params = (user_id,)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                notes = []
                for row in rows:
                    note = dict(row)
                    if note['tags']:
                        note['tags'] = json.loads(note['tags'])
                    notes.append(note)
                return notes
    
    async def delete_note(self, user_id: int, note_id: int):
        """Удаляет заметку"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM notes WHERE user_id = ? AND id = ?
            """, (user_id, note_id))
            await db.commit()
    
    # === WORK STATS ===
    
    async def save_work_stats(self, user_id: int, date: str, 
                             total_records: int, total_sfs: int, 
                             total_sch: int, workers_data: List[Dict]):
        """Сохраняет статистику с сайта"""
        workers_json = json.dumps(workers_data, ensure_ascii=False)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO work_stats 
                (user_id, date, total_records, total_sfs, total_sch, workers_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, date, total_records, total_sfs, total_sch, workers_json))
            await db.commit()
    
    async def get_work_stats(self, user_id: int, date: str = None) -> List[Dict[str, Any]]:
        """Получает статистику"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if date:
                query = """
                    SELECT * FROM work_stats
                    WHERE user_id = ? AND date = ?
                    ORDER BY parsed_at DESC
                    LIMIT 1
                """
                params = (user_id, date)
            else:
                query = """
                    SELECT * FROM work_stats
                    WHERE user_id = ?
                    ORDER BY parsed_at DESC
                    LIMIT 10
                """
                params = (user_id,)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                stats = []
                for row in rows:
                    stat = dict(row)
                    if stat['workers_data']:
                        stat['workers_data'] = json.loads(stat['workers_data'])
                    stats.append(stat)
                return stats
    
    # === REMINDERS ===
    
    async def add_reminder(self, user_id: int, text: str, remind_at: datetime) -> int:
        """Добавляет напоминание"""
        async with aiosqlite.connect(self.db_path) as db:
            # Сохраняем в UTC без timezone info для корректной работы SQLite
            remind_at_utc = remind_at.replace(tzinfo=None) if remind_at.tzinfo else remind_at
            cursor = await db.execute("""
                INSERT INTO reminders (user_id, text, remind_at)
                VALUES (?, ?, ?)
            """, (user_id, text, remind_at_utc.strftime('%Y-%m-%d %H:%M:%S')))
            await db.commit()
            return cursor.lastrowid
    
    async def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """Получает активные напоминания"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute("""
                SELECT id, user_id, text, remind_at
                FROM reminders
                WHERE completed = 0 AND remind_at <= datetime('now')
                ORDER BY remind_at
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def complete_reminder(self, reminder_id: int):
        """Отмечает напоминание как выполненное"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE reminders SET completed = 1 WHERE id = ?
            """, (reminder_id,))
            await db.commit()
    
    async def get_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        """Получает все напоминания пользователя (включая выполненные)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT id, text, remind_at, completed, created_at
                FROM reminders
                WHERE user_id = ?
                ORDER BY remind_at DESC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                reminders = []
                for row in rows:
                    reminder = dict(row)
                    # Парсим дату обратно в datetime объект
                    if reminder['remind_at']:
                        reminder['remind_at'] = datetime.fromisoformat(reminder['remind_at'])
                    if reminder['created_at']:
                        reminder['created_at'] = datetime.fromisoformat(reminder['created_at'])
                    reminders.append(reminder)
                return reminders
    
    # === CONTENT LIBRARY (Умная база знаний) ===
    
    async def save_content(
        self, 
        user_id: int,
        content_type: str,
        title: str = None,
        description: str = None,
        category: str = None,
        file_id: str = None,
        file_path: str = None,
        url: str = None,
        text_content: str = None,
        metadata: dict = None
    ) -> int:
        """
        Сохраняет контент в библиотеку
        
        Args:
            user_id: ID пользователя
            content_type: image, text, code, link, video, document, audio
            title: Название (от пользователя)
            description: Описание (AI generated)
            category: Категория (funny, useful, maps, work, personal, etc.)
            file_id: Telegram file_id (для файлов)
            file_path: Локальный путь (если сохранен на диск)
            url: URL (для ссылок)
            text_content: Текстовый контент
            metadata: JSON метаданные (теги, язык кода, source и т.д.)
            
        Returns:
            ID созданной записи
        """
        metadata_json = json.dumps(metadata or {})
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO content_library 
                (user_id, content_type, title, description, category, 
                 file_id, file_path, url, text_content, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, content_type, title, description, category,
                  file_id, file_path, url, text_content, metadata_json))
            
            await db.commit()
            return cursor.lastrowid
    
    async def get_content(
        self, 
        user_id: int, 
        content_id: int = None,
        content_type: str = None,
        category: str = None,
        search: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Получает контент из библиотеки с фильтрацией
        
        Args:
            user_id: ID пользователя
            content_id: ID конкретного контента
            content_type: Фильтр по типу
            category: Фильтр по категории
            search: Поиск по названию/описанию
            limit: Лимит результатов
            
        Returns:
            Список контента
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = "SELECT * FROM content_library WHERE user_id = ?"
            params = [user_id]
            
            if content_id:
                query += " AND id = ?"
                params.append(content_id)
            
            if content_type:
                query += " AND content_type = ?"
                params.append(content_type)
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if search:
                query += " AND (title LIKE ? OR description LIKE ? OR text_content LIKE ?)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                result = []
                for row in rows:
                    item = dict(row)
                    # Парсим metadata обратно в dict
                    if item.get('metadata'):
                        try:
                            item['metadata'] = json.loads(item['metadata'])
                        except:
                            item['metadata'] = {}
                    result.append(item)
                return result
    
    async def update_content(
        self,
        content_id: int,
        user_id: int,
        title: str = None,
        description: str = None,
        category: str = None,
        metadata: dict = None
    ):
        """Обновляет контент в библиотеке"""
        async with aiosqlite.connect(self.db_path) as db:
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                query = f"UPDATE content_library SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
                params.extend([content_id, user_id])
                
                await db.execute(query, params)
                await db.commit()
    
    async def delete_content(self, content_id: int, user_id: int):
        """Удаляет контент из библиотеки"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM content_library WHERE id = ? AND user_id = ?",
                (content_id, user_id)
            )
            await db.commit()
    
    async def get_categories(self, user_id: int) -> List[str]:
        """Получает список всех категорий пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT DISTINCT category 
                FROM content_library 
                WHERE user_id = ? AND category IS NOT NULL
                ORDER BY category
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    
    async def get_content_stats(self, user_id: int) -> Dict[str, int]:
        """Получает статистику по контенту пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT 
                    content_type,
                    COUNT(*) as count
                FROM content_library
                WHERE user_id = ?
                GROUP BY content_type
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return {row['content_type']: row['count'] for row in rows}

