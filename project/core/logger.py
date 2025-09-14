"""
Система логирования
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

class Logger:
    """Централизованная система логирования"""
    
    def __init__(self, name: str = "shop_bot", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.setup_logging(level)
    
    def setup_logging(self, level: str):
        """Настройка логирования"""
        # Создаем директорию для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Очищаем существующие обработчики
        self.logger.handlers.clear()
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный вывод
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Файловый вывод с ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "bot.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Отдельный файл для ошибок
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def info(self, message: str, **kwargs):
        """Информационное сообщение"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Предупреждение"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, exc_info=None, **kwargs):
        """Ошибка"""
        self.logger.error(message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info=None, **kwargs):
        """Критическая ошибка"""
        self.logger.critical(message, exc_info=exc_info, **kwargs)

# Глобальный логгер
logger = Logger()