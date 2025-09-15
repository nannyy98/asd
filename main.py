import signal
import sys
import threading
from datetime import datetime
from database import DatabaseManager
from handlers import MessageHandler
from notifications import NotificationManager

        # Инициализируем систему автоматических постов
        try:
            from scheduled_posts import ScheduledPostsManager
            self.scheduled_posts = ScheduledPostsManager(self, self.db)
            # Передаем ссылку на бота в менеджер постов
            self.scheduled_posts.bot = self
            logger.info("✅ Система постов инициализирована (ручное управление)")
        except Exception as e:
            logger.warning(f"⚠️ Система постов недоступна: {e}")
            self.scheduled_posts = None