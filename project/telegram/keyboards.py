"""
Клавиатуры для Telegram бота
"""

from typing import List, Dict, Any, Optional

class KeyboardBuilder:
    """Строитель клавиатур"""
    
    @staticmethod
    def main_menu() -> Dict[str, Any]:
        """Главное меню"""
        return {
            'keyboard': [
                ['🛍 Каталог', '🛒 Корзина'],
                ['📋 Мои заказы', '👤 Профиль'],
                ['🔍 Поиск', '❤️ Избранное'],
                ['ℹ️ Помощь']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    
    @staticmethod
    def categories_menu(categories: List) -> Dict[str, Any]:
        """Меню категорий"""
        keyboard = []
        
        for i in range(0, len(categories), 2):
            row = [f"{categories[i][3]} {categories[i][1]}"]
            if i + 1 < len(categories):
                row.append(f"{categories[i + 1][3]} {categories[i + 1][1]}")
            keyboard.append(row)
        
        keyboard.append(['🏠 Главная'])
        
        return {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    
    @staticmethod
    def products_menu(products: List) -> Dict[str, Any]:
        """Меню товаров"""
        keyboard = []
        
        for product in products:
            keyboard.append([f"🛍 {product[1]} - ${product[3]:.2f}"])
        
        keyboard.append(['🔙 К категориям', '🏠 Главная'])
        
        return {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    
    @staticmethod
    def product_quantity_selection(product_id: int, max_stock: int) -> Dict[str, Any]:
        """Выбор количества товара"""
        keyboard = []
        
        # Первый ряд - количество от 1 до 5
        row1 = []
        for i in range(1, min(6, max_stock + 1)):
            row1.append({'text': f'{i} шт.', 'callback_data': f'quantity_{product_id}_{i}'})
        keyboard.append(row1)
        
        # Второй ряд - если есть больше 5 в наличии
        if max_stock > 5:
            row2 = []
            for i in range(6, min(11, max_stock + 1)):
                row2.append({'text': f'{i} шт.', 'callback_data': f'quantity_{product_id}_{i}'})
            if row2:
                keyboard.append(row2)
        
        # Кнопка "Назад"
        keyboard.append([{'text': '🔙 Назад', 'callback_data': 'back_to_catalog'}])
        
        return {
            'inline_keyboard': keyboard
        }
    
    @staticmethod
    def product_actions(product_id: int) -> Dict[str, Any]:
        """Действия с товаром"""
        return {
            'inline_keyboard': [
                [
                    {'text': '🛒 В корзину', 'callback_data': f'add_to_cart_{product_id}'},
                    {'text': '❤️ В избранное', 'callback_data': f'add_to_favorites_{product_id}'}
                ],
                [
                    {'text': '📊 Отзывы', 'callback_data': f'reviews_{product_id}'},
                    {'text': '⭐ Оценить', 'callback_data': f'rate_product_{product_id}'}
                ]
            ]
        }
    
    @staticmethod
    def cart_management(has_items: bool = False) -> Dict[str, Any]:
        """Управление корзиной"""
        keyboard = []
        
        if has_items:
            keyboard.extend([
                ['📦 Оформить заказ'],
                ['🗑 Очистить корзину', '➕ Добавить товары']
            ])
        else:
            keyboard.append(['🛍 Перейти в каталог'])
        
        keyboard.append(['🏠 Главная'])
        
        return {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    
    @staticmethod
    def cart_item_actions(cart_item_id: int, current_quantity: int) -> Dict[str, Any]:
        """Действия с товаром в корзине"""
        return {
            'inline_keyboard': [
                [
                    {'text': '➖', 'callback_data': f'cart_decrease_{cart_item_id}'},
                    {'text': f'📦 {current_quantity}', 'callback_data': f'cart_quantity_{cart_item_id}'},
                    {'text': '➕', 'callback_data': f'cart_increase_{cart_item_id}'}
                ],
                [
                    {'text': '🗑 Удалить', 'callback_data': f'cart_remove_{cart_item_id}'}
                ]
            ]
        }
    
    @staticmethod
    def payment_methods() -> Dict[str, Any]:
        """Способы оплаты"""
        return {
            'keyboard': [
                ['💳 Payme', '🔵 Click'],
                ['💎 Stripe', '🟡 PayPal'],
                ['💵 Наличными при получении'],
                ['❌ Отмена']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
    
    @staticmethod
    def admin_menu() -> Dict[str, Any]:
        """Админ меню"""
        return {
            'keyboard': [
                ['📊 Статистика', '📦 Заказы'],
                ['🛠 Товары', '👥 Пользователи'],
                ['📈 Аналитика', '💰 Финансы'],
                ['📦 Склад', '🎯 Маркетинг'],
                ['🔙 Пользовательский режим']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    
    @staticmethod
    def confirmation() -> Dict[str, Any]:
        """Подтверждение действия"""
        return {
            'keyboard': [
                ['✅ Да', '❌ Нет']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
    
    @staticmethod
    def rating_stars(product_id: int) -> Dict[str, Any]:
        """Оценка товара звездами"""
        return {
            'inline_keyboard': [
                [
                    {'text': '⭐', 'callback_data': f'rate_{product_id}_1'},
                    {'text': '⭐⭐', 'callback_data': f'rate_{product_id}_2'},
                    {'text': '⭐⭐⭐', 'callback_data': f'rate_{product_id}_3'}
                ],
                [
                    {'text': '⭐⭐⭐⭐', 'callback_data': f'rate_{product_id}_4'},
                    {'text': '⭐⭐⭐⭐⭐', 'callback_data': f'rate_{product_id}_5'}
                ],
                [
                    {'text': '❌ Отмена', 'callback_data': 'cancel_rating'}
                ]
            ]
        }
    
    @staticmethod
    def back_button() -> Dict[str, Any]:
        """Кнопка назад"""
        return {
            'keyboard': [
                ['🔙 Назад', '🏠 Главная']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }