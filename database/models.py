"""
Модели данных для SQLite
"""

# SQL схемы таблиц

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings TEXT DEFAULT '{}'
)
"""

CONVERSATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

LONG_TERM_MEMORY_TABLE = """
CREATE TABLE IF NOT EXISTS long_term_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    UNIQUE(user_id, category, key)
)
"""

NOTES_TABLE = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

WORK_STATS_TABLE = """
CREATE TABLE IF NOT EXISTS work_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    total_records INTEGER,
    total_sfs INTEGER,
    total_sch INTEGER,
    workers_data TEXT,
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

REMINDERS_TABLE = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    remind_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

CONTENT_LIBRARY_TABLE = """
CREATE TABLE IF NOT EXISTS content_library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    title TEXT,
    description TEXT,
    category TEXT,
    file_id TEXT,
    file_path TEXT,
    url TEXT,
    text_content TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

# Таблица целей пользователя 🎯
GOALS_TABLE = """
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    goal_type TEXT NOT NULL DEFAULT 'custom',
    status TEXT NOT NULL DEFAULT 'active',
    progress INTEGER DEFAULT 0,
    deadline TIMESTAMP,
    milestones TEXT DEFAULT '[]',
    completed_milestones TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

# Таблица достижений 🏆
ACHIEVEMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    goal_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT '⭐',
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (goal_id) REFERENCES goals (id)
)
"""

# Таблица истории эмоций 💙
EMOTIONAL_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS emotional_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message_preview TEXT,
    emotion TEXT NOT NULL,
    intensity REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    keywords TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

# Таблица адресов ДТЕК 🔌
DTEK_ADDRESSES_TABLE = """
CREATE TABLE IF NOT EXISTS dtek_addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    city TEXT NOT NULL,
    street TEXT NOT NULL,
    building TEXT NOT NULL,
    queue TEXT,
    monitoring_enabled INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
"""

ALL_TABLES = [
    USERS_TABLE,
    CONVERSATIONS_TABLE,
    LONG_TERM_MEMORY_TABLE,
    NOTES_TABLE,
    WORK_STATS_TABLE,
    REMINDERS_TABLE,
    CONTENT_LIBRARY_TABLE,
    GOALS_TABLE,
    ACHIEVEMENTS_TABLE,
    EMOTIONAL_HISTORY_TABLE,
    DTEK_ADDRESSES_TABLE,
]

