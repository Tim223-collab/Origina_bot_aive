"""
Скрипт для проверки напоминаний в БД
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/bot.db')
cursor = conn.cursor()

# Проверяем текущее время БД
cursor.execute("SELECT datetime('now') as now")
db_time = cursor.fetchone()[0]
print(f"\n🕐 Текущее время БД (UTC): {db_time}")

# Получаем все напоминания
cursor.execute("""
    SELECT id, user_id, text, remind_at, completed 
    FROM reminders 
    ORDER BY remind_at DESC
""")

reminders = cursor.fetchall()

if not reminders:
    print("\n❌ Напоминаний в БД нет!\n")
else:
    print(f"\n📋 Напоминаний в БД: {len(reminders)}\n")
    for r in reminders:
        status = "✅ Выполнено" if r[4] == 1 else "⏳ Ожидает"
        print(f"ID {r[0]}: {r[2]}")
        print(f"   Время: {r[3]}")
        print(f"   User: {r[1]}")
        print(f"   Статус: {status}")
        
        # Проверяем должно ли уже сработать
        if r[4] == 0:  # если не выполнено
            cursor.execute("""
                SELECT datetime(?) <= datetime('now') as should_fire
            """, (r[3],))
            should_fire = cursor.fetchone()[0]
            if should_fire:
                print(f"   ⚠️ ДОЛЖНО БЫЛО СРАБОТАТЬ!")
            else:
                print(f"   ⏰ Еще не время")
        print()

conn.close()

