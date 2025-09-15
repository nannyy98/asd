#!/usr/bin/env python3
"""
Создание недостающих модулей для телеграм-бота
"""

import os

def create_handlers_module():
    """Создание модуля handlers.py"""
    handlers_content = '''"""
Обработчики сообщений для телеграм-бота
"""

from keyboards import *
from utils import *
from localization import t, get_user_language

class MessageHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.user_states = {}
        self.notification_manager = None
        self.payment_processor = None
    
    def handle_message(self, message):
        """Основной обработчик сообщений"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            # Получаем пользователя
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            
            if not user_data:
                # Новый пользователь - начинаем регистрацию
                self.start_registration(message)
                return
            
            user_id = user_data[0][0]
            language = user_data[0][5]
            
            # Обрабатываем команды
            if text == '/start':
                self.send_welcome_message(chat_id, language, user_data[0])
            elif text == '/help':
                self.send_help_message(chat_id, language)
            elif text == '🛍 Каталог' or text == '🛍 Katalog':
                self.show_catalog(chat_id, language)
            elif text == '🛒 Корзина' or text == '🛒 Savat':
                self.show_cart(chat_id, user_id, language)
            elif text == '📋 Мои заказы':
                self.show_user_orders(chat_id, user_id, language)
            elif text == '👤 Профиль':
                self.show_user_profile(chat_id, user_id, language)
            elif text == '🔍 Поиск':
                self.start_search(chat_id, language)
            elif text.startswith('🛍 '):
                self.handle_product_selection(message, user_id)
            elif text.startswith('📱 ') or text.startswith('👕 ') or text.startswith('🏠 '):
                self.handle_category_selection(message, user_id)
            else:
                # Проверяем состояние пользователя
                state = self.user_states.get(telegram_id, '')
                if state.startswith('registration_'):
                    self.handle_registration_step(message)
                elif state == 'searching':
                    self.handle_search_query(message, user_id)
                elif state == 'ordering':
                    self.handle_order_process(message, user_id)
                else:
                    self.send_unknown_command(chat_id, language)
                    
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            self.bot.send_message(chat_id, "❌ Произошла ошибка. Попробуйте позже.")
    
    def start_registration(self, message):
        """Начало регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Предлагаем имя из Telegram
        suggested_name = message['from'].get('first_name', '')
        if message['from'].get('last_name'):
            suggested_name += f" {message['from']['last_name']}"
        
        self.user_states[telegram_id] = 'registration_name'
        
        welcome_text = "🛍 <b>Добро пожаловать в наш интернет-магазин!</b>\\n\\n"
        welcome_text += "Для начала работы пройдите быструю регистрацию.\\n\\n"
        welcome_text += "👤 Как вас зовут?"
        
        keyboard = create_registration_keyboard('name', suggested_name)
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def handle_registration_step(self, message):
        """Обработка шагов регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        state = self.user_states.get(telegram_id, '')
        
        if state == 'registration_name':
            if text == '❌ Отмена':
                del self.user_states[telegram_id]
                self.bot.send_message(chat_id, "Регистрация отменена.")
                return
            
            self.user_states[telegram_id] = 'registration_phone'
            self.registration_data = {'name': text}
            
            phone_text = "📱 Поделитесь номером телефона или пропустите этот шаг"
            keyboard = create_registration_keyboard('phone')
            self.bot.send_message(chat_id, phone_text, keyboard)
            
        elif state == 'registration_phone':
            phone = None
            if 'contact' in message:
                phone = message['contact']['phone_number']
            elif text != '⏭ Пропустить' and text != '❌ Отмена':
                phone = text
            
            if text == '❌ Отмена':
                del self.user_states[telegram_id]
                self.bot.send_message(chat_id, "Регистрация отменена.")
                return
            
            self.registration_data['phone'] = phone
            self.user_states[telegram_id] = 'registration_language'
            
            lang_text = "🌍 Выберите язык / Tilni tanlang"
            keyboard = create_registration_keyboard('language')
            self.bot.send_message(chat_id, lang_text, keyboard)
            
        elif state == 'registration_language':
            language = 'ru'
            if text == '🇺🇿 O\'zbekcha':
                language = 'uz'
            
            # Создаем пользователя
            user_id = self.db.add_user(
                telegram_id,
                self.registration_data['name'],
                self.registration_data.get('phone'),
                None,
                language
            )
            
            if user_id:
                del self.user_states[telegram_id]
                
                success_text = t('registration_complete', language=language)
                keyboard = create_main_keyboard()
                self.bot.send_message(chat_id, success_text, keyboard)
            else:
                self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")
    
    def send_welcome_message(self, chat_id, language, user_data):
        """Отправка приветственного сообщения"""
        welcome_text = t('welcome_back', language=language)
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def send_help_message(self, chat_id, language):
        """Отправка справки"""
        help_text = t('help', language=language)
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, help_text, keyboard)
    
    def show_catalog(self, chat_id, language):
        """Показ каталога"""
        categories = self.db.get_categories()
        if categories:
            catalog_text = "🛍 <b>Каталог товаров</b>\\n\\nВыберите категорию:"
            keyboard = create_categories_keyboard(categories)
            self.bot.send_message(chat_id, catalog_text, keyboard)
        else:
            self.bot.send_message(chat_id, "❌ Каталог временно недоступен")
    
    def show_cart(self, chat_id, user_id, language):
        """Показ корзины"""
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            empty_text = t('empty_cart', language=language)
            keyboard = create_cart_keyboard(False)
            self.bot.send_message(chat_id, empty_text, keyboard)
            return
        
        cart_text = "🛒 <b>Ваша корзина:</b>\\n\\n"
        total = 0
        
        for item in cart_items:
            item_total = item[2] * item[3]
            total += item_total
            cart_text += f"• {item[1]} × {item[3]} = {format_price(item_total)}\\n"
        
        cart_text += f"\\n💰 <b>Итого: {format_price(total)}</b>"
        
        keyboard = create_cart_keyboard(True)
        self.bot.send_message(chat_id, cart_text, keyboard)
    
    def show_user_orders(self, chat_id, user_id, language):
        """Показ заказов пользователя"""
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            self.bot.send_message(chat_id, "📋 У вас пока нет заказов")
            return
        
        orders_text = "📋 <b>Ваши заказы:</b>\\n\\n"
        
        for order in orders[:10]:  # Показываем последние 10
            status_emoji = get_order_status_emoji(order[3])
            orders_text += f"{status_emoji} Заказ #{order[0]} - {format_price(order[2])}\\n"
            orders_text += f"📅 {format_date(order[7])}\\n\\n"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, orders_text, keyboard)
    
    def show_user_profile(self, chat_id, user_id, language):
        """Показ профиля пользователя"""
        user = self.db.execute_query('SELECT * FROM users WHERE id = ?', (user_id,))[0]
        
        profile_text = f"👤 <b>Ваш профиль</b>\\n\\n"
        profile_text += f"📝 Имя: {user[2]}\\n"
        if user[3]:
            profile_text += f"📱 Телефон: {user[3]}\\n"
        if user[4]:
            profile_text += f"📧 Email: {user[4]}\\n"
        profile_text += f"🌍 Язык: {'Русский' if user[5] == 'ru' else 'O\\'zbekcha'}\\n"
        profile_text += f"📅 Регистрация: {format_date(user[7])}"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, profile_text, keyboard)
    
    def handle_callback_query(self, callback_query):
        """Обработка callback запросов"""
        try:
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            if data.startswith('add_to_cart_'):
                product_id = int(data.split('_')[3])
                self.add_product_to_cart(chat_id, user_id, product_id)
            elif data.startswith('cart_increase_'):
                cart_item_id = int(data.split('_')[2])
                self.update_cart_item_quantity(chat_id, cart_item_id, 1)
            elif data.startswith('cart_decrease_'):
                cart_item_id = int(data.split('_')[2])
                self.update_cart_item_quantity(chat_id, cart_item_id, -1)
            elif data.startswith('cart_remove_'):
                cart_item_id = int(data.split('_')[2])
                self.remove_cart_item(chat_id, cart_item_id)
                
        except Exception as e:
            print(f"Ошибка обработки callback: {e}")
    
    def add_product_to_cart(self, chat_id, user_id, product_id):
        """Добавление товара в корзину"""
        result = self.db.add_to_cart(user_id, product_id, 1)
        
        if result:
            self.bot.send_message(chat_id, "✅ Товар добавлен в корзину!")
        else:
            self.bot.send_message(chat_id, "❌ Товар недоступен или закончился")
    
    def send_unknown_command(self, chat_id, language):
        """Отправка сообщения о неизвестной команде"""
        unknown_text = "❓ Команда не распознана. Используйте меню ниже."
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, unknown_text, keyboard)
'''
    
    with open('handlers.py', 'w', encoding='utf-8') as f:
        f.write(handlers_content)
    print("✅ Создан handlers.py")

def create_admin_module():
    """Создание модуля admin.py"""
    admin_content = '''"""
Админ-панель для телеграм-бота
"""

from keyboards import create_admin_keyboard, create_back_keyboard
from utils import format_price, format_date

class AdminHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.admin_states = {}
        self.notification_manager = None
    
    def handle_admin_command(self, message):
        """Обработка админ команд"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            # Проверяем права админа
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data or not user_data[0][6]:  # is_admin
                self.bot.send_message(chat_id, "❌ У вас нет прав администратора")
                return
            
            if text == '/admin' or text == '📊 Статистика':
                self.show_admin_panel(chat_id)
            elif text == '📦 Заказы':
                self.show_orders_management(chat_id)
            elif text == '🛠 Товары':
                self.show_products_management(chat_id)
            elif text == '👥 Пользователи':
                self.show_users_stats(chat_id)
            elif text == '🔙 Пользовательский режим':
                self.exit_admin_mode(chat_id)
                
        except Exception as e:
            print(f"Ошибка админ команды: {e}")
    
    def show_admin_panel(self, chat_id):
        """Показ админ панели"""
        stats = self.get_basic_stats()
        
        admin_text = f"🛡 <b>Админ-панель</b>\\n\\n"
        admin_text += f"📊 <b>Статистика:</b>\\n"
        admin_text += f"👥 Пользователей: {stats['users']}\\n"
        admin_text += f"🛍 Товаров: {stats['products']}\\n"
        admin_text += f"📦 Заказов: {stats['orders']}\\n"
        admin_text += f"💰 Выручка: {format_price(stats['revenue'])}\\n\\n"
        admin_text += f"Выберите действие:"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, admin_text, keyboard)
    
    def get_basic_stats(self):
        """Получение базовой статистики"""
        try:
            users_count = self.db.execute_query('SELECT COUNT(*) FROM users WHERE is_admin = 0')[0][0]
            products_count = self.db.execute_query('SELECT COUNT(*) FROM products WHERE is_active = 1')[0][0]
            orders_count = self.db.execute_query('SELECT COUNT(*) FROM orders')[0][0]
            revenue = self.db.execute_query('SELECT SUM(total_amount) FROM orders WHERE status != "cancelled"')[0][0] or 0
            
            return {
                'users': users_count,
                'products': products_count,
                'orders': orders_count,
                'revenue': revenue
            }
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {'users': 0, 'products': 0, 'orders': 0, 'revenue': 0}
    
    def show_orders_management(self, chat_id):
        """Управление заказами"""
        recent_orders = self.db.execute_query('''
            SELECT o.id, o.total_amount, o.status, o.created_at, u.name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 10
        ''')
        
        if not recent_orders:
            self.bot.send_message(chat_id, "📦 Заказов пока нет")
            return
        
        orders_text = "📦 <b>Последние заказы:</b>\\n\\n"
        
        for order in recent_orders:
            status_emoji = get_order_status_emoji(order[2])
            orders_text += f"{status_emoji} #{order[0]} - {format_price(order[1])}\\n"
            orders_text += f"👤 {order[4]}\\n"
            orders_text += f"📅 {format_date(order[3])}\\n\\n"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, orders_text, keyboard)
    
    def show_products_management(self, chat_id):
        """Управление товарами"""
        products = self.db.execute_query('''
            SELECT id, name, price, stock, is_active
            FROM products
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        if not products:
            self.bot.send_message(chat_id, "🛍 Товаров пока нет")
            return
        
        products_text = "🛍 <b>Товары:</b>\\n\\n"
        
        for product in products:
            status = "✅" if product[4] else "❌"
            products_text += f"{status} {product[1]}\\n"
            products_text += f"💰 {format_price(product[2])} | 📦 {product[3]} шт.\\n\\n"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, products_text, keyboard)
    
    def show_users_stats(self, chat_id):
        """Статистика пользователей"""
        stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN created_at >= date('now', '-7 days') THEN 1 END) as new_users_week,
                COUNT(CASE WHEN language = 'uz' THEN 1 END) as uzbek_users
            FROM users
            WHERE is_admin = 0
        ''')[0]
        
        users_text = f"👥 <b>Статистика пользователей:</b>\\n\\n"
        users_text += f"📊 Всего: {stats[0]}\\n"
        users_text += f"🆕 Новых за неделю: {stats[1]}\\n"
        users_text += f"🇺🇿 Узбекский язык: {stats[2]}\\n"
        users_text += f"🇷🇺 Русский язык: {stats[0] - stats[2]}"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, users_text, keyboard)
    
    def exit_admin_mode(self, chat_id):
        """Выход из админ режима"""
        welcome_text = "👤 Переключено в пользовательский режим"
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def handle_callback_query(self, callback_query):
        """Обработка админ callback'ов"""
        pass
'''
    
    with open('admin.py', 'w', encoding='utf-8') as f:
        f.write(admin_content)
    print("✅ Создан admin.py")

def main():
    """Создание недостающих модулей"""
    print("🔧 Создание недостающих модулей...")
    
    if not os.path.exists('handlers.py'):
        create_handlers_module()
    else:
        print("✅ handlers.py уже существует")
    
    if not os.path.exists('admin.py'):
        create_admin_module()
    else:
        print("✅ admin.py уже существует")
    
    print("\\n🎉 Все модули созданы!")
    print("🚀 Теперь можно запускать бота: python main.py")

if __name__ == "__main__":
    main()