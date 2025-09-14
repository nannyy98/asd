"""
Утилиты общего назначения
"""

import re
from datetime import datetime
from typing import Optional, Union
from decimal import Decimal

def format_price(price: Union[float, Decimal, int]) -> str:
    """Форматирование цены"""
    return f"${float(price):.2f}"

def format_date(date_input: Union[str, datetime]) -> str:
    """Форматирование даты"""
    try:
        if isinstance(date_input, str):
            if 'T' in date_input:
                date_obj = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
            else:
                date_obj = datetime.strptime(date_input, '%Y-%m-%d %H:%M:%S')
        else:
            date_obj = date_input
        return date_obj.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return str(date_input)

def validate_email(email: str) -> bool:
    """Валидация email"""
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> Optional[str]:
    """Валидация и очистка номера телефона"""
    if not phone:
        return None
    
    clean_phone = re.sub(r'[^\d+]', '', phone)
    if len(clean_phone) >= 10 and (clean_phone.startswith('+') or clean_phone.isdigit()):
        return clean_phone
    return None

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Очистка текста от опасных символов"""
    if not text:
        return ""
    
    # Удаляем потенциально опасные символы
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text[:max_length]

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def escape_html(text: str) -> str:
    """Экранирование HTML символов"""
    if not text:
        return ""
    
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))

def calculate_cart_total(cart_items: list) -> float:
    """Подсчет общей суммы корзины"""
    return sum(item[2] * item[3] for item in cart_items)

def get_status_emoji(status: str) -> str:
    """Получение эмодзи для статуса"""
    status_emojis = {
        'pending': '⏳',
        'confirmed': '✅',
        'shipped': '🚚',
        'delivered': '📦',
        'cancelled': '❌'
    }
    return status_emojis.get(status, '❓')

def create_stars_display(rating: float) -> str:
    """Создание отображения звезд для рейтинга"""
    full_stars = int(rating)
    half_star = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    stars = '⭐' * full_stars
    if half_star:
        stars += '✨'
    stars += '☆' * empty_stars
    
    return stars