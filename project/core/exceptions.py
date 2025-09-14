"""
Кастомные исключения для системы
"""

class ShopBotException(Exception):
    """Базовое исключение для бота"""
    pass

class DatabaseError(ShopBotException):
    """Ошибка базы данных"""
    pass

class ValidationError(ShopBotException):
    """Ошибка валидации данных"""
    pass

class SecurityError(ShopBotException):
    """Ошибка безопасности"""
    pass

class PaymentError(ShopBotException):
    """Ошибка платежной системы"""
    pass

class NotificationError(ShopBotException):
    """Ошибка системы уведомлений"""
    pass

class InventoryError(ShopBotException):
    """Ошибка управления складом"""
    pass