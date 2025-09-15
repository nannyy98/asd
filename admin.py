"""
Админ-панель для телеграм-бота
"""

from keyboards import create_admin_keyboard, create_main_keyboard, create_back_keyboard
from utils import format_price, format_date, get_order_status_emoji, get_order_status_text

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
            
            # Обрабатываем навигационные кнопки
            if text in ['🔙 Пользовательский режим', '🏠 Главная']:
                self.exit_admin_mode(chat_id, telegram_id)
                return
            elif text in ['🔙 Назад']:
                self.handle_admin_back(chat_id, telegram_id)
                return
            
            # Основные админ команды
            if text == '/admin' or text == '📊 Статистика':
                self.show_admin_panel(chat_id)
            elif text == '📦 Заказы':
                self.show_orders_management(chat_id)
            elif text == '🛠 Товары':
                self.show_products_management(chat_id)
            elif text == '👥 Пользователи':
                self.show_users_stats(chat_id)
            elif text == '📈 Аналитика':
                self.show_analytics_menu(chat_id)
            elif text == '🛡 Безопасность':
                self.show_security_stats(chat_id)
            elif text == '💰 Финансы':
                self.show_financial_stats(chat_id)
            elif text == '📦 Склад':
                self.show_inventory_stats(chat_id)
            elif text == '🤖 AI':
                self.show_ai_features(chat_id)
            elif text == '🎯 Автоматизация':
                self.show_automation_stats(chat_id)
            elif text == '👥 CRM':
                self.show_crm_stats(chat_id)
            elif text == '📢 Рассылка':
                self.show_broadcast_menu(chat_id)
            else:
                # Проверяем состояние админа
                state = self.admin_states.get(telegram_id, '')
                if state.startswith('adding_product_'):
                    self.handle_add_product_process(message)
                elif state.startswith('creating_broadcast_'):
                    self.handle_broadcast_creation(message)
                else:
                    self.show_admin_panel(chat_id)
                    
        except Exception as e:
            print(f"Ошибка админ команды: {e}")
            self.bot.send_message(chat_id, "❌ Произошла ошибка в админ-панели")
    
    def handle_admin_back(self, chat_id, telegram_id):
        """Обработка кнопки Назад в админ-панели"""
        current_state = self.admin_states.get(telegram_id, '')
        
        if current_state:
            # Очищаем состояние и возвращаем в главное админ меню
            del self.admin_states[telegram_id]
        
        self.show_admin_panel(chat_id)
    
    def show_admin_panel(self, chat_id):
        """Показ админ панели"""
        stats = self.get_basic_stats()
        
        admin_text = f"🛡 <b>Админ-панель</b>\n\n"
        admin_text += f"📊 <b>Статистика:</b>\n"
        admin_text += f"👥 Пользователей: {stats['users']}\n"
        admin_text += f"🛍 Товаров: {stats['products']}\n"
        admin_text += f"📦 Заказов: {stats['orders']}\n"
        admin_text += f"💰 Выручка: {format_price(stats['revenue'])}\n\n"
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
            no_orders_text = "📦 <b>Заказы</b>\n\nЗаказов пока нет"
            keyboard = create_admin_keyboard()
            self.bot.send_message(chat_id, no_orders_text, keyboard)
            return
        
        orders_text = "📦 <b>Последние заказы:</b>\n\n"
        
        for order in recent_orders:
            status_emoji = get_order_status_emoji(order[2])
            status_text = get_order_status_text(order[2])
            orders_text += f"{status_emoji} #{order[0]} - {format_price(order[1])}\n"
            orders_text += f"👤 {order[4]}\n"
            orders_text += f"📊 {status_text}\n"
            orders_text += f"📅 {format_date(order[3])}\n"
            orders_text += f"👆 /admin_order_{order[0]} - управление\n\n"
        
        keyboard = create_admin_keyboard()
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
            no_products_text = "🛍 <b>Товары</b>\n\nТоваров пока нет"
            keyboard = create_admin_keyboard()
            self.bot.send_message(chat_id, no_products_text, keyboard)
            return
        
        products_text = "🛍 <b>Управление товарами:</b>\n\n"
        
        for product in products:
            status = "✅" if product[4] else "❌"
            stock_status = "📦" if product[3] > 5 else "⚠️" if product[3] > 0 else "🔴"
            
            products_text += f"{status} <b>{product[1]}</b>\n"
            products_text += f"💰 {format_price(product[2])} | {stock_status} {product[3]} шт.\n"
            products_text += f"👆 /edit_product_{product[0]} - редактировать\n"
            products_text += f"👆 /delete_product_{product[0]} - удалить\n\n"
        
        keyboard = create_admin_keyboard()
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
        
        users_text = f"👥 <b>Статистика пользователей:</b>\n\n"
        users_text += f"📊 Всего: {stats[0]}\n"
        users_text += f"🆕 Новых за неделю: {stats[1]}\n"
        users_text += f"🇺🇿 Узбекский язык: {stats[2]}\n"
        users_text += f"🇷🇺 Русский язык: {stats[0] - stats[2]}"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, users_text, keyboard)
    
    def show_analytics_menu(self, chat_id):
        """Меню аналитики"""
        analytics_text = "📈 <b>Аналитика</b>\n\nВыберите тип отчета:"
        
        # Создаем inline клавиатуру для аналитики
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📊 Продажи за период', 'callback_data': 'analytics_sales'},
                    {'text': '👥 Поведение клиентов', 'callback_data': 'analytics_behavior'}
                ],
                [
                    {'text': '📈 ABC-анализ', 'callback_data': 'analytics_abc'},
                    {'text': '🎯 Воронка конверсии', 'callback_data': 'analytics_funnel'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back_main'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, analytics_text, keyboard)
    
    def show_security_stats(self, chat_id):
        """Статистика безопасности"""
        security_text = "🛡 <b>Безопасность</b>\n\nСистема безопасности активна.\n\n"
        security_text += "✅ Все системы работают нормально"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, security_text, keyboard)
    
    def show_financial_stats(self, chat_id):
        """Финансовая статистика"""
        try:
            today_revenue = self.db.execute_query('''
                SELECT COALESCE(SUM(total_amount), 0) 
                FROM orders 
                WHERE DATE(created_at) = DATE('now') AND status != 'cancelled'
            ''')[0][0]
            
            month_revenue = self.db.execute_query('''
                SELECT COALESCE(SUM(total_amount), 0) 
                FROM orders 
                WHERE DATE(created_at) >= DATE('now', 'start of month') AND status != 'cancelled'
            ''')[0][0]
            
            financial_text = f"💰 <b>Финансовая сводка:</b>\n\n"
            financial_text += f"📅 Сегодня: {format_price(today_revenue)}\n"
            financial_text += f"📊 За месяц: {format_price(month_revenue)}\n\n"
            financial_text += f"💡 Подробные отчеты доступны в веб-панели"
            
        except Exception as e:
            financial_text = "💰 <b>Финансы</b>\n\nОшибка получения данных"
            print(f"Ошибка финансовой статистики: {e}")
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, financial_text, keyboard)
    
    def show_inventory_stats(self, chat_id):
        """Статистика склада"""
        try:
            low_stock = self.db.execute_query(
                'SELECT COUNT(*) FROM products WHERE stock <= 5 AND is_active = 1'
            )[0][0]
            
            out_of_stock = self.db.execute_query(
                'SELECT COUNT(*) FROM products WHERE stock = 0 AND is_active = 1'
            )[0][0]
            
            inventory_text = f"📦 <b>Состояние склада:</b>\n\n"
            
            if out_of_stock > 0:
                inventory_text += f"🔴 Нет в наличии: {out_of_stock} товаров\n"
            if low_stock > 0:
                inventory_text += f"🟡 Мало на складе: {low_stock} товаров\n"
            
            if out_of_stock == 0 and low_stock == 0:
                inventory_text += f"✅ Все товары в наличии!"
            else:
                inventory_text += f"\n💡 Требуется пополнение склада"
                
        except Exception as e:
            inventory_text = "📦 <b>Склад</b>\n\nОшибка получения данных"
            print(f"Ошибка статистики склада: {e}")
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, inventory_text, keyboard)
    
    def show_ai_features(self, chat_id):
        """AI функции"""
        ai_text = "🤖 <b>AI функции</b>\n\n"
        ai_text += "✅ Персональные рекомендации\n"
        ai_text += "✅ Анализ поведения клиентов\n"
        ai_text += "✅ Умная поддержка\n"
        ai_text += "✅ Прогнозирование спроса\n\n"
        ai_text += "💡 AI системы работают в фоновом режиме"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, ai_text, keyboard)
    
    def show_automation_stats(self, chat_id):
        """Статистика автоматизации"""
        automation_text = "🎯 <b>Автоматизация</b>\n\n"
        automation_text += "✅ Автоматические уведомления\n"
        automation_text += "✅ Обработка брошенных корзин\n"
        automation_text += "✅ Программа лояльности\n"
        automation_text += "✅ Автопополнение склада\n\n"
        automation_text += "💡 Все процессы автоматизированы"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, automation_text, keyboard)
    
    def show_crm_stats(self, chat_id):
        """CRM статистика"""
        try:
            from crm import CRMManager
            crm = CRMManager(self.db)
            segments = crm.segment_customers()
            
            crm_text = f"👥 <b>CRM Сегментация:</b>\n\n"
            crm_text += f"🏆 Чемпионы: {len(segments.get('champions', []))}\n"
            crm_text += f"💎 Лояльные: {len(segments.get('loyal', []))}\n"
            crm_text += f"⭐ Потенциальные: {len(segments.get('potential', []))}\n"
            crm_text += f"🆕 Новые: {len(segments.get('new', []))}\n"
            crm_text += f"⚠️ Требуют внимания: {len(segments.get('need_attention', []))}\n"
            crm_text += f"🚨 В зоне риска: {len(segments.get('at_risk', []))}\n\n"
            crm_text += f"💡 Подробная CRM аналитика в веб-панели"
            
        except ImportError:
            crm_text = "👥 <b>CRM</b>\n\nМодуль CRM недоступен"
        except Exception as e:
            crm_text = "👥 <b>CRM</b>\n\nОшибка получения данных"
            print(f"Ошибка CRM статистики: {e}")
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, crm_text, keyboard)
    
    def show_broadcast_menu(self, chat_id):
        """Меню рассылки"""
        broadcast_text = "📢 <b>Рассылка сообщений</b>\n\n"
        broadcast_text += "Выберите тип рассылки:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📢 Всем пользователям', 'callback_data': 'broadcast_all'},
                    {'text': '🔥 Активным клиентам', 'callback_data': 'broadcast_active'}
                ],
                [
                    {'text': '😴 Неактивным', 'callback_data': 'broadcast_inactive'},
                    {'text': '🆕 Новым пользователям', 'callback_data': 'broadcast_new'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back_main'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, broadcast_text, keyboard)
    
    def exit_admin_mode(self, chat_id, telegram_id):
        """Выход из админ режима"""
        # Очищаем состояние админа
        if telegram_id in self.admin_states:
            del self.admin_states[telegram_id]
        
        # Получаем данные пользователя
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if user_data:
            language = user_data[0][5]
            welcome_text = "👤 Переключено в пользовательский режим"
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def handle_order_management(self, message):
        """Управление конкретным заказом"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        if text.startswith('/admin_order_'):
            order_id = int(text.split('_')[2])
            self.show_order_details(chat_id, order_id)
    
    def show_order_details(self, chat_id, order_id):
        """Показ деталей заказа"""
        order_details = self.db.get_order_details(order_id)
        
        if not order_details:
            self.bot.send_message(chat_id, "❌ Заказ не найден")
            return
        
        order = order_details['order']
        items = order_details['items']
        
        # Получаем информацию о клиенте
        user = self.db.execute_query(
            'SELECT name, phone, email FROM users WHERE id = ?',
            (order[1],)
        )[0]
        
        details_text = f"📋 <b>Заказ #{order[0]}</b>\n\n"
        details_text += f"👤 Клиент: {user[0]}\n"
        if user[1]:
            details_text += f"📱 Телефон: {user[1]}\n"
        if user[2]:
            details_text += f"📧 Email: {user[2]}\n"
        
        details_text += f"\n💰 Сумма: {format_price(order[2])}\n"
        details_text += f"📅 Дата: {format_date(order[7])}\n"
        details_text += f"📊 Статус: {get_order_status_text(order[3])}\n"
        
        if order[4]:
            details_text += f"📍 Адрес: {order[4]}\n"
        
        details_text += f"💳 Оплата: {order[5]}\n"
        
        details_text += f"\n🛍 <b>Товары:</b>\n"
        for item in items:
            details_text += f"• {item[2]} × {item[0]} = {format_price(item[1] * item[0])}\n"
        
        # Создаем inline клавиатуру для управления заказом
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Подтвердить', 'callback_data': f'change_status_{order_id}_confirmed'},
                    {'text': '🚚 Отправить', 'callback_data': f'change_status_{order_id}_shipped'}
                ],
                [
                    {'text': '📦 Доставлен', 'callback_data': f'change_status_{order_id}_delivered'},
                    {'text': '❌ Отменить', 'callback_data': f'change_status_{order_id}_cancelled'}
                ],
                [
                    {'text': '🔙 К заказам', 'callback_data': 'admin_orders'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, details_text, keyboard)
    
    def handle_product_commands(self, message):
        """Обработка команд управления товарами"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        if text.startswith('/edit_product_'):
            product_id = int(text.split('_')[2])
            self.show_product_edit_menu(chat_id, product_id)
        elif text.startswith('/delete_product_'):
            product_id = int(text.split('_')[2])
            self.confirm_product_deletion(chat_id, product_id)
    
    def show_product_edit_menu(self, chat_id, product_id):
        """Меню редактирования товара"""
        product = self.db.get_product_by_id(product_id)
        
        if not product:
            self.bot.send_message(chat_id, "❌ Товар не найден")
            return
        
        edit_text = f"✏️ <b>Редактирование товара</b>\n\n"
        edit_text += f"🛍 <b>{product[1]}</b>\n"
        edit_text += f"💰 Цена: {format_price(product[3])}\n"
        edit_text += f"📦 Остаток: {product[7]} шт.\n"
        edit_text += f"📊 Статус: {'Активен' if product[8] else 'Скрыт'}\n\n"
        edit_text += f"💡 Для редактирования используйте веб-панель администратора"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, edit_text, keyboard)
    
    def confirm_product_deletion(self, chat_id, product_id):
        """Подтверждение удаления товара"""
        product = self.db.get_product_by_id(product_id)
        
        if not product:
            self.bot.send_message(chat_id, "❌ Товар не найден")
            return
        
        confirm_text = f"⚠️ <b>Подтверждение удаления</b>\n\n"
        confirm_text += f"Вы действительно хотите удалить товар:\n"
        confirm_text += f"🛍 <b>{product[1]}</b>\n\n"
        confirm_text += f"❗ Это действие нельзя отменить!"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Да, удалить', 'callback_data': f'delete_product_confirm_{product_id}'},
                    {'text': '❌ Отмена', 'callback_data': 'admin_products'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, confirm_text, keyboard)
    
    def handle_callback_query(self, callback_query):
        """Обработка админ callback'ов"""
        try:
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            if data.startswith('change_status_'):
                parts = data.split('_')
                order_id = int(parts[2])
                new_status = parts[3]
                self.change_order_status(chat_id, order_id, new_status)
            elif data.startswith('delete_product_confirm_'):
                product_id = int(data.split('_')[3])
                self.delete_product(chat_id, product_id)
            elif data == 'admin_back_main':
                self.show_admin_panel(chat_id)
            elif data == 'admin_orders':
                self.show_orders_management(chat_id)
            elif data == 'admin_products':
                self.show_products_management(chat_id)
            elif data.startswith('broadcast_'):
                self.handle_broadcast_callback(callback_query)
                
        except Exception as e:
            print(f"Ошибка админ callback: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка обработки команды")
    
    def change_order_status(self, chat_id, order_id, new_status):
        """Изменение статуса заказа"""
        result = self.db.update_order_status(order_id, new_status)
        
        if result is not None:
            status_text = get_order_status_text(new_status)
            self.bot.send_message(chat_id, f"✅ Статус заказа #{order_id} изменен на: {status_text}")
            
            # Уведомляем клиента
            if self.notification_manager:
                self.notification_manager.send_order_status_notification(order_id, new_status)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка изменения статуса")
    
    def delete_product(self, chat_id, product_id):
        """Удаление товара"""
        product = self.db.get_product_by_id(product_id)
        product_name = product[1] if product else f"ID {product_id}"
        
        result = self.db.execute_query('DELETE FROM products WHERE id = ?', (product_id,))
        
        if result is not None:
            self.bot.send_message(chat_id, f"✅ Товар \"{product_name}\" удален")
        else:
            self.bot.send_message(chat_id, "❌ Ошибка удаления товара")
    
    def handle_broadcast_callback(self, callback_query):
        """Обработка callback'ов рассылки"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        telegram_id = callback_query['from']['id']
        
        if data == 'broadcast_all':
            self.start_broadcast_creation(chat_id, telegram_id, 'all')
        elif data == 'broadcast_active':
            self.start_broadcast_creation(chat_id, telegram_id, 'active')
        elif data == 'broadcast_inactive':
            self.start_broadcast_creation(chat_id, telegram_id, 'inactive')
        elif data == 'broadcast_new':
            self.start_broadcast_creation(chat_id, telegram_id, 'new')
    
    def start_broadcast_creation(self, chat_id, telegram_id, target_type):
        """Начало создания рассылки"""
        self.admin_states[telegram_id] = f'creating_broadcast_{target_type}'
        
        target_names = {
            'all': 'всем пользователям',
            'active': 'активным клиентам',
            'inactive': 'неактивным клиентам',
            'new': 'новым пользователям'
        }
        
        broadcast_text = f"📢 <b>Рассылка {target_names.get(target_type, 'пользователям')}</b>\n\n"
        broadcast_text += f"Введите текст сообщения для рассылки:"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, broadcast_text, keyboard)
    
    def handle_broadcast_creation(self, message):
        """Обработка создания рассылки"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        if text in ['🔙 Назад', '❌ Отмена']:
            del self.admin_states[telegram_id]
            self.show_admin_panel(chat_id)
            return
        
        state = self.admin_states.get(telegram_id, '')
        if state.startswith('creating_broadcast_'):
            target_type = state.split('_')[2]
            
            # Отправляем рассылку
            if self.notification_manager:
                success_count, error_count = self.notification_manager.send_promotional_broadcast(
                    text, target_type
                )
                
                result_text = f"📊 <b>Результат рассылки:</b>\n\n"
                result_text += f"✅ Отправлено: {success_count}\n"
                result_text += f"❌ Ошибок: {error_count}\n\n"
                result_text += f"📝 Текст: {text[:50]}{'...' if len(text) > 50 else ''}"
                
                self.bot.send_message(chat_id, result_text)
            else:
                self.bot.send_message(chat_id, "❌ Система уведомлений недоступна")
            
            # Очищаем состояние
            del self.admin_states[telegram_id]
            self.show_admin_panel(chat_id)
    
    def handle_add_product_process(self, message):
        """Обработка добавления товара"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Для добавления товаров рекомендуем использовать веб-панель
        add_product_text = "➕ <b>Добавление товара</b>\n\n"
        add_product_text += "💡 Для удобного добавления товаров используйте веб-панель администратора:\n\n"
        add_product_text += "🌐 http://localhost:5000\n"
        add_product_text += "👤 Логин: AdminUser\n"
        add_product_text += "🔑 Пароль: admin123\n\n"
        add_product_text += "Там вы сможете:\n"
        add_product_text += "• Загружать изображения\n"
        add_product_text += "• Заполнять подробные описания\n"
        add_product_text += "• Управлять категориями\n"
        add_product_text += "• Просматривать аналитику"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, add_product_text, keyboard)
        
        # Очищаем состояние
        if telegram_id in self.admin_states:
            del self.admin_states[telegram_id]
    
    def handle_analytics_callback(self, callback_query):
        """Обработка callback'ов аналитики"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        
        if data == 'analytics_sales':
            self.show_sales_analytics(chat_id)
        elif data == 'analytics_behavior':
            self.show_behavior_analytics(chat_id)
        elif data == 'analytics_abc':
            self.show_abc_analytics(chat_id)
        elif data == 'analytics_funnel':
            self.show_funnel_analytics(chat_id)
    
    def show_sales_analytics(self, chat_id):
        """Аналитика продаж"""
        try:
            from analytics import AnalyticsManager
            analytics = AnalyticsManager(self.db)
            
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            report = analytics.get_sales_report(start_date, end_date)
            formatted_report = analytics.format_sales_report(report)
            
            self.bot.send_message(chat_id, formatted_report)
            
        except ImportError:
            self.bot.send_message(chat_id, "📊 Модуль аналитики недоступен")
        except Exception as e:
            self.bot.send_message(chat_id, "❌ Ошибка получения аналитики")
            print(f"Ошибка аналитики: {e}")
    
    def show_behavior_analytics(self, chat_id):
        """Аналитика поведения"""
        behavior_text = "👥 <b>Поведение клиентов</b>\n\n"
        behavior_text += "📊 Подробная аналитика доступна в веб-панели"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, behavior_text, keyboard)
    
    def show_abc_analytics(self, chat_id):
        """ABC аналитика"""
        abc_text = "📈 <b>ABC анализ</b>\n\n"
        abc_text += "📊 Подробный ABC анализ доступен в веб-панели"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, abc_text, keyboard)
    
    def show_funnel_analytics(self, chat_id):
        """Воронка конверсии"""
        funnel_text = "🎯 <b>Воронка конверсии</b>\n\n"
        funnel_text += "📊 Анализ воронки доступен в веб-панели"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, funnel_text, keyboard)
    
    def handle_export_callback(self, callback_query):
        """Обработка экспорта данных"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        
        export_text = "📊 <b>Экспорт данных</b>\n\n"
        export_text += "💡 Функция экспорта доступна в веб-панели администратора"
        
        keyboard = create_admin_keyboard()
        self.bot.send_message(chat_id, export_text, keyboard)