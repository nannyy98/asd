"""
Модели данных для базы данных
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

@dataclass
class User:
    """Модель пользователя"""
    id: Optional[int] = None
    telegram_id: int = 0
    name: str = ""
    phone: Optional[str] = None
    email: Optional[str] = None
    language: str = "ru"
    is_admin: bool = False
    created_at: Optional[datetime] = None

@dataclass
class Category:
    """Модель категории"""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    emoji: str = "📦"
    is_active: bool = True
    created_at: Optional[datetime] = None

@dataclass
class Product:
    """Модель товара"""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    price: Decimal = Decimal('0.00')
    cost_price: Decimal = Decimal('0.00')
    category_id: int = 0
    brand: Optional[str] = None
    image_url: Optional[str] = None
    stock: int = 0
    views: int = 0
    sales_count: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None

@dataclass
class Order:
    """Модель заказа"""
    id: Optional[int] = None
    user_id: int = 0
    total_amount: Decimal = Decimal('0.00')
    status: str = "pending"
    delivery_address: Optional[str] = None
    payment_method: str = "cash"
    payment_status: str = "pending"
    promo_discount: Decimal = Decimal('0.00')
    delivery_cost: Decimal = Decimal('0.00')
    created_at: Optional[datetime] = None

@dataclass
class CartItem:
    """Модель элемента корзины"""
    id: Optional[int] = None
    user_id: int = 0
    product_id: int = 0
    quantity: int = 1
    created_at: Optional[datetime] = None

@dataclass
class Review:
    """Модель отзыва"""
    id: Optional[int] = None
    user_id: int = 0
    product_id: int = 0
    rating: int = 5
    comment: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass
class PromoCode:
    """Модель промокода"""
    id: Optional[int] = None
    code: str = ""
    discount_type: str = "percentage"
    discount_value: Decimal = Decimal('0.00')
    min_order_amount: Decimal = Decimal('0.00')
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    description: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None