"""
Менеджер базы данных с улучшенной архитектурой
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any, Tuple
from contextlib import contextmanager

from core.logger import logger
from core.exceptions import DatabaseError
from core.config import config
from .models import User, Product, Category, Order, CartItem

class DatabaseManager:
    """Улучшенный менеджер базы данных"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database.path
        self.ensure_database_directory()
        self.init_database()
    
    def ensure_database_directory(self):
        """Создание директории для базы данных"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка базы данных: {e}", exc_info=True)
            raise DatabaseError(f"Database error: {e}")
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Optional[List]:
        """Выполнение SQL запроса"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                self._create_tables(cursor)
                
                if self._is_database_empty(cursor):
                    self._create_initial_data(cursor)
                
                conn.commit()
                logger.info("База данных инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}", exc_info=True)
            raise DatabaseError(f"Database initialization failed: {e}")
    
    def _create_tables(self, cursor):
        """Создание таблиц"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                language TEXT DEFAULT 'ru',
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                emoji TEXT DEFAULT '📦',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                cost_price REAL DEFAULT 0,
                category_id INTEGER,
                brand TEXT,
                image_url TEXT,
                stock INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                sales_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                total_amount REAL,
                status TEXT DEFAULT 'pending',
                delivery_address TEXT,
                payment_method TEXT DEFAULT 'cash',
                payment_status TEXT DEFAULT 'pending',
                promo_discount REAL DEFAULT 0,
                delivery_cost REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id),
                UNIQUE(user_id, product_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_type TEXT NOT NULL,
                discount_value REAL NOT NULL,
                min_order_amount REAL DEFAULT 0,
                max_uses INTEGER,
                expires_at TIMESTAMP,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        self._create_indexes(cursor)
    
    def _create_indexes(self, cursor):
        """Создание индексов"""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)',
            'CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)',
            'CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_cart_user ON cart(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    def _is_database_empty(self, cursor) -> bool:
        """Проверка пустоты базы данных"""
        cursor.execute('SELECT COUNT(*) FROM categories')
        return cursor.fetchone()[0] == 0
    
    def _create_initial_data(self, cursor):
        """Создание начальных данных"""
        # Создаем админа
        if config.bot.admin_telegram_id:
            try:
                admin_id = int(config.bot.admin_telegram_id)
                cursor.execute('''
                    INSERT OR IGNORE INTO users (telegram_id, name, is_admin, language)
                    VALUES (?, ?, 1, 'ru')
                ''', (admin_id, config.bot.admin_name))
                logger.info(f"Админ создан: {config.bot.admin_name}")
            except ValueError:
                logger.warning(f"Неверный ADMIN_TELEGRAM_ID: {config.bot.admin_telegram_id}")
        
        # Категории
        categories = [
            ('Электроника', 'Смартфоны, ноутбуки, гаджеты', '📱'),
            ('Одежда', 'Мужская и женская одежда', '👕'),
            ('Дом и сад', 'Товары для дома и дачи', '🏠'),
            ('Спорт', 'Спортивные товары и инвентарь', '⚽'),
            ('Красота', 'Косметика и парфюмерия', '💄'),
            ('Книги', 'Художественная и техническая литература', '📚')
        ]
        
        cursor.executemany(
            'INSERT INTO categories (name, description, emoji) VALUES (?, ?, ?)',
            categories
        )
        
        # Товары
        products = [
            ('iPhone 15 Pro', 'Новейший смартфон Apple', 999.99, 750.00, 1, 'Apple', 
             'https://images.pexels.com/photos/788946/pexels-photo-788946.jpeg', 25),
            ('Samsung Galaxy S24', 'Флагманский смартфон Samsung', 899.99, 650.00, 1, 'Samsung',
             'https://images.pexels.com/photos/1092644/pexels-photo-1092644.jpeg', 30),
            ('MacBook Pro M3', 'Профессиональный ноутбук Apple', 1999.99, 1500.00, 1, 'Apple',
             'https://images.pexels.com/photos/18105/pexels-photo.jpg', 15),
            ('Футболка Nike', 'Спортивная футболка премиум качества', 49.99, 25.00, 2, 'Nike',
             'https://images.pexels.com/photos/8532616/pexels-photo-8532616.jpeg', 100),
            ('Джинсы Levi\'s', 'Классические джинсы высокого качества', 89.99, 45.00, 2, 'Levi\'s',
             'https://images.pexels.com/photos/1598507/pexels-photo-1598507.jpeg', 75)
        ]
        
        cursor.executemany('''
            INSERT INTO products (name, description, price, cost_price, category_id, brand, image_url, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', products)
        
        # Промокоды
        promo_codes = [
            ('WELCOME10', 'percentage', 10, 0, None, None, 'Скидка для новых клиентов'),
            ('SAVE20', 'percentage', 20, 100, 100, None, 'Скидка при заказе от $100')
        ]
        
        cursor.executemany('''
            INSERT INTO promo_codes (code, discount_type, discount_value, min_order_amount, max_uses, expires_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', promo_codes)
    
    # Методы для работы с пользователями
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[List]:
        """Получение пользователя по telegram_id"""
        return self.execute_query(
            'SELECT * FROM users WHERE telegram_id = ?',
            (telegram_id,)
        )
    
    def create_user(self, telegram_id: int, name: str, phone: str = None, 
                   email: str = None, language: str = 'ru') -> Optional[int]:
        """Создание нового пользователя"""
        existing = self.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,)
        )
        
        if existing:
            return existing[0][0]
        
        return self.execute_query('''
            INSERT INTO users (telegram_id, name, phone, email, language)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, name, phone, email, language))
    
    # Методы для работы с товарами
    def get_categories(self) -> List:
        """Получение всех активных категорий"""
        return self.execute_query(
            'SELECT * FROM categories WHERE is_active = 1 ORDER BY name'
        )
    
    def get_products_by_category(self, category_id: int, limit: int = 10, offset: int = 0) -> List:
        """Получение товаров по категории"""
        return self.execute_query('''
            SELECT * FROM products 
            WHERE category_id = ? AND is_active = 1 
            ORDER BY name 
            LIMIT ? OFFSET ?
        ''', (category_id, limit, offset))
    
    def get_product_by_id(self, product_id: int) -> Optional[List]:
        """Получение товара по ID"""
        result = self.execute_query(
            'SELECT * FROM products WHERE id = ?',
            (product_id,)
        )
        return result[0] if result else None
    
    def search_products(self, query: str, limit: int = 10) -> List:
        """Поиск товаров"""
        return self.execute_query('''
            SELECT * FROM products 
            WHERE (name LIKE ? OR description LIKE ?) AND is_active = 1
            ORDER BY views DESC, sales_count DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
    
    # Методы для работы с корзиной
    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> Optional[int]:
        """Добавление товара в корзину"""
        # Проверяем наличие товара
        product = self.execute_query(
            'SELECT stock FROM products WHERE id = ? AND is_active = 1',
            (product_id,)
        )
        
        if not product or product[0][0] < quantity:
            return None
        
        # Проверяем существующий товар в корзине
        existing = self.execute_query(
            'SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?',
            (user_id, product_id)
        )
        
        if existing:
            new_quantity = existing[0][1] + quantity
            if new_quantity > product[0][0]:
                return None
            
            return self.execute_query(
                'UPDATE cart SET quantity = ? WHERE id = ?',
                (new_quantity, existing[0][0])
            )
        else:
            return self.execute_query(
                'INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                (user_id, product_id, quantity)
            )
    
    def get_cart_items(self, user_id: int) -> List:
        """Получение товаров из корзины"""
        return self.execute_query('''
            SELECT c.id, p.name, p.price, c.quantity, p.image_url, p.id as product_id
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
            ORDER BY c.created_at DESC
        ''', (user_id,))
    
    def clear_cart(self, user_id: int) -> Optional[int]:
        """Очистка корзины"""
        return self.execute_query(
            'DELETE FROM cart WHERE user_id = ?',
            (user_id,)
        )
    
    # Методы для работы с заказами
    def create_order(self, user_id: int, total_amount: float, 
                    delivery_address: str, payment_method: str) -> Optional[int]:
        """Создание заказа"""
        return self.execute_query('''
            INSERT INTO orders (user_id, total_amount, delivery_address, payment_method)
            VALUES (?, ?, ?, ?)
        ''', (user_id, total_amount, delivery_address, payment_method))
    
    def add_order_items(self, order_id: int, cart_items: List):
        """Добавление товаров в заказ"""
        for item in cart_items:
            self.execute_query('''
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item[5], item[3], item[2]))
    
    def get_user_orders(self, user_id: int) -> List:
        """Получение заказов пользователя"""
        return self.execute_query('''
            SELECT * FROM orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
    
    def get_order_details(self, order_id: int) -> Optional[dict]:
        """Получение деталей заказа"""
        order = self.execute_query(
            'SELECT * FROM orders WHERE id = ?',
            (order_id,)
        )
        
        if not order:
            return None
        
        items = self.execute_query('''
            SELECT oi.quantity, oi.price, p.name, p.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order_id,))
        
        return {
            'order': order[0],
            'items': items
        }
    
    def update_order_status(self, order_id: int, status: str) -> Optional[int]:
        """Обновление статуса заказа"""
        return self.execute_query(
            'UPDATE orders SET status = ? WHERE id = ?',
            (status, order_id)
        )
    
    # Методы для работы с отзывами
    def add_review(self, user_id: int, product_id: int, rating: int, comment: str = None) -> Optional[int]:
        """Добавление отзыва"""
        return self.execute_query('''
            INSERT INTO reviews (user_id, product_id, rating, comment)
            VALUES (?, ?, ?, ?)
        ''', (user_id, product_id, rating, comment))
    
    def get_product_reviews(self, product_id: int) -> List:
        """Получение отзывов на товар"""
        return self.execute_query('''
            SELECT r.rating, r.comment, r.created_at, u.name
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE r.product_id = ?
            ORDER BY r.created_at DESC
        ''', (product_id,))
    
    # Методы для работы с избранным
    def add_to_favorites(self, user_id: int, product_id: int) -> Optional[int]:
        """Добавление в избранное"""
        return self.execute_query('''
            INSERT OR IGNORE INTO favorites (user_id, product_id)
            VALUES (?, ?)
        ''', (user_id, product_id))
    
    def get_user_favorites(self, user_id: int) -> List:
        """Получение избранных товаров"""
        return self.execute_query('''
            SELECT p.* FROM products p
            JOIN favorites f ON p.id = f.product_id
            WHERE f.user_id = ? AND p.is_active = 1
            ORDER BY f.created_at DESC
        ''', (user_id,))
    
    # Методы для работы с уведомлениями
    def add_notification(self, user_id: int, title: str, message: str, 
                        notification_type: str = 'info') -> Optional[int]:
        """Добавление уведомления"""
        return self.execute_query('''
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, title, message, notification_type))
    
    def get_unread_notifications(self, user_id: int) -> List:
        """Получение непрочитанных уведомлений"""
        return self.execute_query('''
            SELECT * FROM notifications 
            WHERE user_id = ? AND is_read = 0
            ORDER BY created_at DESC
        ''', (user_id,))