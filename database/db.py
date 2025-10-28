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

