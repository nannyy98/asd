"""
Главный файл запуска телеграм-бота интернет-магазина
Версия 2.0 - Полностью переработанная архитектура
"""

import os
import sys
import signal
import time
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.config import config
from core.logger import logger
from core.exceptions import ShopBotException
from database.manager import DatabaseManager
from telegram.bot import TelegramBot
from telegram.handlers import MessageHandler
from services.notification_service import NotificationService
from services.payment_service import PaymentService
from services.analytics_service import AnalyticsService

class ShopBotApplication:
    """Главное приложение бота"""
    
    def __init__(self, token: str):
        self.token = token
        self.running = True
        
        # Инициализация компонентов
        self.db = DatabaseManager()
        self.bot = TelegramBot(token)
        self.message_handler = MessageHandler(self.bot, self.db)
        self.notification_service = NotificationService(self.bot, self.db)
        self.payment_service = PaymentService()
        self.analytics_service = AnalyticsService(self.db)
        
        # Связываем компоненты
        self.message_handler.notification_service = self.notification_service
        self.message_handler.payment_service = self.payment_service
        
        # Настройка обработчиков сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🛍 Telegram Shop Bot v2.0 инициализирован")
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.running = False
        self.bot.stop()
        sys.exit(0)
    
    def run(self):
        """Запуск основного цикла бота"""
        logger.info("🚀 Запуск бота...")
        logger.info("📱 Ожидание сообщений...")
        logger.info("Нажмите Ctrl+C для остановки")
        
        error_count = 0
        max_errors = 10
        
        try:
            while self.running:
                try:
                    updates = self.bot.get_updates()
                    
                    if updates and updates.get('ok'):
                        error_count = 0  # Сбрасываем счетчик при успехе
                        
                        for update in updates['result']:
                            self.bot.offset = update['update_id'] + 1
                            
                            try:
                                if 'message' in update:
                                    self.message_handler.handle_message(update['message'])
                                elif 'callback_query' in update:
                                    self.message_handler.handle_callback_query(update['callback_query'])
                                    
                            except Exception as e:
                                logger.error(f"Ошибка обработки обновления: {e}", exc_info=True)
                    else:
                        error_count += 1
                        if error_count >= max_errors:
                            logger.critical("Превышено максимальное количество ошибок")
                            time.sleep(60)
                            error_count = 0
                    
                    time.sleep(0.1)  # Небольшая пауза
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Ошибка в основном цикле: {e}", exc_info=True)
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Бот остановлен пользователем")
        finally:
            logger.info("🔄 Завершение работы...")
            self.running = False

def main():
    """Главная функция"""
    # Создаем необходимые директории
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Получение токена
    token = config.bot.token
    
    if not token:
        # Fallback токен для тестирования
        token = "8292684103:AAH0TKL-lCOaKVeppjtAdmsx0gdeMrGtjdQ"
    
    if not token or token == 'YOUR_BOT_TOKEN':
        logger.critical("❌ Токен бота не установлен!")
        print("\n📋 Инструкция по настройке:")
        print("1. Создайте бота через @BotFather в Telegram")
        print("2. Получите токен бота")
        print("3. Установите переменную окружения:")
        print("   export TELEGRAM_BOT_TOKEN='ваш_токен'")
        print("\n🔗 Подробная инструкция в README.md")
        return
    
    try:
        # Запуск приложения
        app = ShopBotApplication(token)
        app.run()
        
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка запуска: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()