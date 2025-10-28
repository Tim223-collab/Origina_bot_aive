"""
Обработчики рабочих команд
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from datetime import datetime

from database import Database
from services import WorkSiteParser


class WorkHandler:
    def __init__(self, db: Database, parser: WorkSiteParser):
        self.db = db
        self.parser = parser
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /stats [дата] - получает статистику с сайта
        """
        user = update.effective_user
        
        # Парсим дату из аргументов
        date = None
        if context.args:
            date = context.args[0]
        
        await update.message.reply_text("🔄 Получаю статистику с сайта...")
        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            # Парсим данные
            stats = await self.parser.parse_statistics(date)
            
            if not stats:
                await update.message.reply_text(
                    "❌ Не удалось получить статистику. Проверь доступность сайта."
                )
                return
            
            # Сохраняем в БД
            await self.db.save_work_stats(
                user_id=user.id,
                date=date or datetime.now().strftime('%Y-%m-%d'),
                total_records=stats['total_records'],
                total_sfs=stats['total_sfs'],
                total_sch=stats['total_sch'],
                workers_data=stats['workers']
            )
            
            # Формируем красивый ответ
            message = f"""📊 **Статистика работы**

📝 Всего записей: **{stats['total_records']}**
✅ Успешных (SFS): **{stats['total_sfs']}**
📋 Проверено (SCH): **{stats['total_sch']}**
👥 Активных сотрудников: **{len(stats['workers'])}**

**Топ-5 работников по SFS:**
"""
            
            # Сортируем работников
            top_workers = sorted(
                stats['workers'], 
                key=lambda x: x.get('sfs', 0), 
                reverse=True
            )[:5]
            
            for i, worker in enumerate(top_workers, 1):
                team_emoji = "💚" if "Good Bunny" in worker.get('team', '') else "💙"
                message += f"\n{i}. {team_emoji} **{worker['name']}**"
                message += f"\n   SFS: {worker.get('sfs', 0)} | Only now: {worker.get('only_now', 0)} | SCH: {worker.get('sch', 0)}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            print(f"❌ Ошибка при получении статистики: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при парсинге данных."
            )
    
    async def workers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /workers [команда] - показывает список работников
        """
        user = update.effective_user
        
        # Фильтр по команде
        team_filter = None
        if context.args:
            team_filter = " ".join(context.args)
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            stats = await self.parser.parse_statistics()
            
            if not stats:
                await update.message.reply_text("❌ Не удалось получить данные.")
                return
            
            workers = stats['workers']
            
            # Фильтруем по команде если указано
            if team_filter:
                workers = [w for w in workers if team_filter.lower() in w.get('team', '').lower()]
            
            if not workers:
                await update.message.reply_text("👥 Работники не найдены.")
                return
            
            # Формируем сообщение
            message = f"👥 **Список работников** ({len(workers)})\n\n"
            
            for worker in workers[:20]:  # Ограничиваем 20 для читаемости
                team_emoji = "💚" if "Good Bunny" in worker.get('team', '') else "💙"
                message += f"{team_emoji} **{worker['name']}** {worker.get('username', '')}\n"
                message += f"   SFS: {worker.get('sfs', 0)} | SCH: {worker.get('sch', 0)}\n"
            
            if len(workers) > 20:
                message += f"\n_...и еще {len(workers) - 20} работников_"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await update.message.reply_text("❌ Произошла ошибка.")
    
    async def check_worker_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /check <имя> - проверяет конкретного работника
        """
        if not context.args:
            await update.message.reply_text(
                "❓ Использование: /check <имя работника>"
            )
            return
        
        worker_name = " ".join(context.args)
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            stats = await self.parser.parse_statistics()
            
            if not stats:
                await update.message.reply_text("❌ Не удалось получить данные.")
                return
            
            # Ищем работника
            found = None
            for worker in stats['workers']:
                if worker_name.lower() in worker['name'].lower():
                    found = worker
                    break
            
            if not found:
                await update.message.reply_text(
                    f"🔍 Работник **{worker_name}** не найден."
                )
                return
            
            # Формируем детальную информацию
            team_emoji = "💚" if "Good Bunny" in found.get('team', '') else "💙"
            
            message = f"""{team_emoji} **{found['name']}**
            
👤 Username: {found.get('username', 'Не указан')}
🏷 Команда: {found.get('team', 'Не указана')}
📅 Дата отчета: {found.get('date', 'Не указана')}

📊 **Показатели:**
✅ SFS: **{found.get('sfs', 0)}**
⏰ Only now: **{found.get('only_now', 0)}**
📋 SCH: **{found.get('sch', 0)}**
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await update.message.reply_text("❌ Произошла ошибка.")

