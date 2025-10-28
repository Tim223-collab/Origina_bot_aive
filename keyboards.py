"""
Клавиатуры для Telegram бота
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def get_main_menu():
    """
    Главное меню с кнопками быстрого доступа
    """
    keyboard = [
        [
            KeyboardButton("💬 Диалог"),
            KeyboardButton("📊 Статистика"),
        ],
        [
            KeyboardButton("📝 Заметки"),
            KeyboardButton("🧠 Память"),
        ],
        [
            KeyboardButton("🌤 Погода"),
            KeyboardButton("💰 Курсы"),
        ],
        [
            KeyboardButton("🎲 Игры"),
            KeyboardButton("ℹ️ Помощь"),
        ],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выбери команду или напиши сообщение..."
    )


def get_stats_menu():
    """
    Меню статистики
    """
    keyboard = [
        [
            KeyboardButton("/stats"),
            KeyboardButton("/workers"),
        ],
        [
            KeyboardButton("/check"),
            KeyboardButton("🏠 Главное меню"),
        ],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


def get_notes_menu():
    """
    Меню заметок
    """
    keyboard = [
        [
            KeyboardButton("/note"),
            KeyboardButton("/notes"),
        ],
        [
            KeyboardButton("/remind"),
            KeyboardButton("🏠 Главное меню"),
        ],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


def get_memory_menu():
    """
    Меню памяти
    """
    keyboard = [
        [
            KeyboardButton("/remember"),
            KeyboardButton("/recall"),
        ],
        [
            KeyboardButton("/forget"),
            KeyboardButton("🏠 Главное меню"),
        ],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


def get_info_menu():
    """
    Меню информации
    """
    keyboard = [
        [
            KeyboardButton("/weather Київ"),
            KeyboardButton("/weather Харків"),
        ],
        [
            KeyboardButton("/rates"),
            KeyboardButton("/crypto BTC"),
        ],
        [
            KeyboardButton("🏠 Главное меню"),
        ],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


def get_games_menu():
    """
    Меню игр и развлечений
    """
    keyboard = [
        [
            KeyboardButton("/joke"),
            KeyboardButton("/quote"),
        ],
        [
            KeyboardButton("/fact"),
            KeyboardButton("/dice"),
        ],
        [
            KeyboardButton("/8ball"),
            KeyboardButton("/tips"),
        ],
        [
            KeyboardButton("🏠 Главное меню"),
        ],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


def remove_keyboard():
    """
    Удаляет клавиатуру
    """
    return ReplyKeyboardRemove()

