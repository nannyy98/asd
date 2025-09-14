"""
Централизованная конфигурация системы
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    path: str = "data/shop_bot.db"
    backup_interval: int = 3600
    max_connections: int = 10

@dataclass
class SecurityConfig:
    """Конфигурация безопасности"""
    rate_limit_per_minute: int = 20
    max_failed_attempts: int = 5
    block_duration_hours: int = 24
    jwt_secret: str = "change-in-production"

@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str
    name: str = "Shop Bot"
    admin_telegram_id: Optional[str] = None
    admin_name: str = "Admin"
    currency: str = "USD"
    currency_symbol: str = "$"
    max_message_length: int = 4096

@dataclass
class AppConfig:
    """Главная конфигурация приложения"""
    environment: str = "development"
    debug: bool = True
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    bot: BotConfig = field(default_factory=lambda: BotConfig(token=""))

def load_config() -> AppConfig:
    """Загрузка конфигурации из переменных окружения"""
    return AppConfig(
        environment=os.getenv('ENVIRONMENT', 'development'),
        debug=os.getenv('DEBUG', 'true').lower() == 'true',
        database=DatabaseConfig(
            path=os.getenv('DATABASE_PATH', 'data/shop_bot.db'),
            backup_interval=int(os.getenv('BACKUP_INTERVAL', '3600')),
            max_connections=int(os.getenv('MAX_CONNECTIONS', '10'))
        ),
        security=SecurityConfig(
            rate_limit_per_minute=int(os.getenv('RATE_LIMIT', '20')),
            max_failed_attempts=int(os.getenv('MAX_FAILED_ATTEMPTS', '5')),
            block_duration_hours=int(os.getenv('BLOCK_DURATION', '24')),
            jwt_secret=os.getenv('JWT_SECRET', 'change-in-production')
        ),
        bot=BotConfig(
            token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            name=os.getenv('BOT_NAME', 'Shop Bot'),
            admin_telegram_id=os.getenv('ADMIN_TELEGRAM_ID'),
            admin_name=os.getenv('ADMIN_NAME', 'Admin'),
            currency=os.getenv('CURRENCY', 'USD'),
            currency_symbol=os.getenv('CURRENCY_SYMBOL', '$')
        )
    )

# Глобальная конфигурация
config = load_config()