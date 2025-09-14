"""
Обработчики сообщений Telegram бота
"""

from typing import Dict, Any, Optional, List
from core.logger import logger
from core.utils import format_price, calculate_cart_total, sanitize_text
from core.exceptions import ValidationError
from .keyboards import KeyboardBuilder

class MessageHandler:
    """Обработчик сообщений"""
    
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.user_states = {}
        self.keyboards = KeyboardBuilder()
    
    def handle_message(self, message: Dict[str, Any]):
        """Основной обработчик сообщений"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            # Проверяем регистрацию пользователя
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            
            if not user_data and text != '/start':
                self._send_registration_prompt(chat_id)
                return
            
            # Обрабатываем команды
            if text.startswith('/'):
                self._handle_command(message, user_data)
            else:
                self._handle_text_message(message, user_data)
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            self.bot.send_message(
                message['chat']['id'],
                "❌ Произошла ошибка. Попробуйте позже."
            )
    
    def handle_callback_query(self, callback_query: Dict[str, Any]):
        """Обработчик callback запросов"""
        try:
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            if data.startswith('add_to_cart_'):
                self._handle_add_to_cart(chat_id, data, user_id)
            elif data.startswith('quantity_'):
                self._handle_quantity_selection(chat_id, data, user_id, callback_query)
            elif data.startswith('order_product_'):
                self._handle_order_product(chat_id, data, user_id)
            elif data == 'goto_cart':
                self._show_cart(chat_id, user_id)
            elif data == 'continue_shopping':
                self._show_catalog(chat_id)
            elif data == 'back_to_main':
                self._show_main_menu(chat_id, user_data[0][2])
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}", exc_info=True)
    
    def _handle_command(self, message: Dict[str, Any], user_data: Optional[List]):
        """Обработка команд"""
        text = message['text']
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        if text == '/start':
            if user_data:
                self._show_main_menu(chat_id, user_data[0][2])
            else:
                self._start_registration(message)
        elif text == '/help':
            self._show_help(chat_id)
        elif text.startswith('/order_'):
            self._show_order_details(chat_id, text, user_data[0][0])
        elif text == '/admin' and user_data and user_data[0][6]:
            self._show_admin_menu(chat_id)
    
    def _handle_text_message(self, message: Dict[str, Any], user_data: List):
        """Обработка текстовых сообщений"""
        text = message['text']
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        user_id = user_data[0][0]
        
        # Проверяем состояние пользователя
        if telegram_id in self.user_states:
            self._handle_user_state(message, user_data)
            return
        
        # Обрабатываем меню
        if text == '🛍 Каталог':
            self._show_catalog(chat_id)
        elif text == '🛒 Корзина':
            self._show_cart(chat_id, user_id)
        elif text == '📋 Мои заказы':
            self._show_user_orders(chat_id, user_id)
        elif text == '👤 Профиль':
            self._show_profile(chat_id, user_data[0])
        elif text == '🔍 Поиск':
            self._start_search(chat_id, telegram_id)
        elif text == '❤️ Избранное':
            self._show_favorites(chat_id, user_id)
        elif text == 'ℹ️ Помощь':
            self._show_help(chat_id)
        elif text == '🔙 Назад':
            self._show_main_menu(chat_id, user_data[0][2])
        elif text == '🔙 К категориям':
            self._show_catalog(chat_id)
        elif text == '🏠 Главная':
            self._show_main_menu(chat_id, user_data[0][2])
        elif text.startswith('📱') or text.startswith('👕') or text.startswith('🏠') or text.startswith('⚽') or text.startswith('💄') or text.startswith('📚'):
            self._handle_category_selection(chat_id, text)
        elif text.startswith('🛍'):
            self._handle_product_selection(chat_id, text, user_id)
        else:
            # Поиск товаров
            self._search_products(chat_id, text)
    
    def _start_registration(self, message: Dict[str, Any]):
        """Начало регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Получаем имя из Telegram
        suggested_name = message['from'].get('first_name', '')
        
        self.user_states[telegram_id] = {
            'state': 'registration_name',
            'data': {}
        }
        
        welcome_text = """
🛍 <b>Добро пожаловать в наш интернет-магазин!</b>

Для начала работы нужно пройти быструю регистрацию.

👤 <b>Введите ваше имя:</b>
(Только имя, без фамилии)
        """
        
        keyboard = {
            'keyboard': [[suggested_name]] if suggested_name else [],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def _handle_user_state(self, message: Dict[str, Any], user_data: List):
        """Обработка состояний пользователя"""
        telegram_id = message['from']['id']
        chat_id = message['chat']['id']
        text = message['text']
        
        state_info = self.user_states[telegram_id]
        state = state_info['state']
        
        if state == 'registration_name':
            self._handle_registration_name(message, state_info)
        elif state == 'registration_phone':
            self._handle_registration_phone(message, state_info)
        elif state == 'registration_email':
            self._handle_registration_email(message, state_info)
        elif state == 'search_products':
            self._search_products(chat_id, text)
            del self.user_states[telegram_id]
        elif state == 'checkout_address':
            self._handle_checkout_address(message, user_data[0][0])
        elif state.startswith('quantity_'):
            self._handle_quantity_input(message, state_info, user_data[0][0])
    
    def _handle_checkout_address(self, message: Dict[str, Any], user_id: int):
        """Обработка адреса при оформлении заказа"""
        telegram_id = message['from']['id']
        chat_id = message['chat']['id']
        
        if message.get('text') == '❌ Отмена':
            del self.user_states[telegram_id]
            self._show_cart(chat_id, user_id)
            return
        
        address = ""
        
        # Обработка геолокации
        if 'location' in message:
            lat = message['location']['latitude']
            lon = message['location']['longitude']
            address = f"Геолокация: {lat}, {lon}"
        # Обработка текстового адреса
        elif 'text' in message:
            address = sanitize_text(message['text'], 200)
        
        if not address:
            self.bot.send_message(chat_id, "❌ Пожалуйста, укажите адрес доставки")
            return
        
        # Получаем данные корзины
        state_info = self.user_states[telegram_id]
        cart_items = state_info['data']['cart_items']
        total = calculate_cart_total(cart_items)
        
        # Создаем заказ
        order_id = self.db.create_order(
            user_id=user_id,
            total_amount=total,
            delivery_address=address,
            payment_method="cash"
        )
        
        if order_id:
            # Добавляем товары в заказ
            for item in cart_items:
                self.db.execute_query('''
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                ''', (order_id, item[5], item[3], item[2]))
                
                # Уменьшаем остаток на складе
                self.db.execute_query('''
                    UPDATE products SET stock = stock - ?, sales_count = sales_count + ?
                    WHERE id = ?
                ''', (item[3], item[3], item[5]))
            
            # Очищаем корзину
            self.db.clear_cart(user_id)
            
            # Удаляем состояние
            del self.user_states[telegram_id]
            
            # Отправляем подтверждение
            success_text = f"""
✅ <b>Заказ #{order_id} успешно оформлен!</b>

📦 Товаров: {len(cart_items)}
💰 Сумма: {format_price(total)}
📍 Адрес: {address}
💳 Оплата: Наличными при получении

📞 Мы свяжемся с вами в ближайшее время для подтверждения.

Спасибо за покупку! 🎉
            """
            
            self.bot.send_message(chat_id, success_text, self.keyboards.main_menu())
            
            # Уведомляем админов
            if hasattr(self, 'notification_service'):
                self.notification_service.notify_order_created(order_id)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка создания заказа")
            del self.user_states[telegram_id]
    
    def _handle_registration_name(self, message: Dict[str, Any], state_info: Dict):
        """Обработка ввода имени при регистрации"""
        telegram_id = message['from']['id']
        chat_id = message['chat']['id']
        name = sanitize_text(message['text'], 50)
        
        if len(name) < 2:
            self.bot.send_message(chat_id, "❌ Имя должно содержать минимум 2 символа")
            return
        
        # Завершаем регистрацию сразу с именем
        user_id = self.db.create_user(
            telegram_id=telegram_id,
            name=name
        )
        
        if user_id:
            del self.user_states[telegram_id]
            
            success_text = f"""
✅ <b>Регистрация завершена!</b>

Добро пожаловать в наш магазин, {name}! 🎉

Теперь вы можете:
• Просматривать каталог товаров
• Добавлять товары в корзину
• Оформлять заказы

Приятных покупок! 🛍
            """
            
            self.bot.send_message(chat_id, success_text, self.keyboards.main_menu())
        else:
            self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")
    
    def _handle_registration_phone(self, message: Dict[str, Any], state_info: Dict):
        """Обработка ввода телефона"""
        telegram_id = message['from']['id']
        chat_id = message['chat']['id']
        
        phone = None
        if 'contact' in message:
            phone = message['contact']['phone_number']
        elif message['text'] != '⏭ Пропустить':
            phone = message['text']
        
        state_info['data']['phone'] = phone
        state_info['state'] = 'registration_email'
        
        email_text = "📧 <b>Укажите email для уведомлений</b>\n\nИли пропустите этот шаг."
        
        keyboard = {
            'keyboard': [['⏭ Пропустить']],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.bot.send_message(chat_id, email_text, keyboard)
    
    def _handle_registration_email(self, message: Dict[str, Any], state_info: Dict):
        """Обработка ввода email"""
        telegram_id = message['from']['id']
        chat_id = message['chat']['id']
        
        email = None
        if message['text'] != '⏭ Пропустить':
            email = message['text']
            if not self._validate_email(email):
                self.bot.send_message(chat_id, "❌ Неверный формат email. Попробуйте еще раз или пропустите.")
                return
        
        # Завершаем регистрацию
        data = state_info['data']
        user_id = self.db.create_user(
            telegram_id=telegram_id,
            name=data['name'],
            phone=data.get('phone'),
            email=email
        )
        
        if user_id:
            del self.user_states[telegram_id]
            
            # Показываем сводку регистрации
            summary_text = f"""
✅ <b>Регистрация завершена!</b>

📋 <b>Ваши данные:</b>
👤 Имя: {data['name']}
📱 Телефон: {data.get('phone') or 'Не указан'}
📧 Email: {email or 'Не указан'}

Добро пожаловать в наш магазин! 🎉

Теперь вы можете:
• Просматривать каталог товаров
• Добавлять товары в корзину  
• Оформлять заказы

Приятных покупок! 🛍
            """
            
            self.bot.send_message(chat_id, summary_text, self.keyboards.main_menu())
        else:
            self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")
            success_text = f"""
✅ <b>Регистрация завершена!</b>

Добро пожаловать в наш магазин, {data['name']}! 🎉

Теперь вы можете:
• Просматривать каталог товаров
• Добавлять товары в корзину
• Оформлять заказы

Приятных покупок! 🛍
            """
            
            self.bot.send_message(chat_id, success_text, self.keyboards.main_menu())
        else:
            self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")
    
    def _show_main_menu(self, chat_id: int, name: str):
        """Показ главного меню"""
        welcome_text = f"""
👋 <b>Добро пожаловать, {name}!</b>

Выберите действие из меню:
        """
        
        self.bot.send_message(chat_id, welcome_text, self.keyboards.main_menu())
    
    def _show_catalog(self, chat_id: int):
        """Показ каталога"""
        categories = self.db.get_categories()
        
        if not categories:
            self.bot.send_message(chat_id, "❌ Каталог временно недоступен")
            return
        
        catalog_text = "🛍 <b>Каталог товаров</b>\n\nВыберите категорию:"
        
        self.bot.send_message(
            chat_id, 
            catalog_text, 
            self.keyboards.categories_menu(categories)
        )
    
    def _show_cart(self, chat_id: int, user_id: int):
        """Показ корзины"""
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            empty_text = """
🛒 <b>Ваша корзина пуста</b>

Перейдите в каталог, чтобы добавить товары!
            """
            self.bot.send_message(chat_id, empty_text, self.keyboards.cart_management(False))
            return
        
        total = calculate_cart_total(cart_items)
        
        cart_text = "🛒 <b>Ваша корзина</b>\n\n"
        
        for item in cart_items:
            item_total = item[2] * item[3]
            cart_text += f"🛍 <b>{item[1]}</b>\n"
            cart_text += f"💰 {format_price(item[2])} × {item[3]} шт. = <b>{format_price(item_total)}</b>\n"
            cart_text += f"ID товара: {item[5]}\n\n"
        
        cart_text += f"💳 <b>Общая сумма: {format_price(total)}</b>\n"
        cart_text += f"📦 Товаров в корзине: {len(cart_items)}"
        
        # Отправляем корзину с inline кнопками для каждого товара
        keyboard = self._create_cart_keyboard(cart_items)
        self.bot.send_message(chat_id, cart_text, keyboard)
    
    def _show_user_orders(self, chat_id: int, user_id: int):
        """Показ заказов пользователя"""
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            no_orders_text = """
📋 <b>У вас пока нет заказов</b>

Перейдите в каталог и сделайте первую покупку!
            """
            self.bot.send_message(chat_id, no_orders_text, self.keyboards.back_button())
            return
        
        orders_text = "📋 <b>Ваши заказы</b>\n\n"
        
        for order in orders[:10]:  # Показываем последние 10
            status_emoji = self._get_status_emoji(order[3])
            orders_text += f"{status_emoji} Заказ #{order[0]} - {format_price(order[2])}\n"
            orders_text += f"📅 {order[7][:16]}\n\n"
        
        self.bot.send_message(chat_id, orders_text, self.keyboards.back_button())
    
    def _show_profile(self, chat_id: int, user_data: List):
        """Показ профиля пользователя"""
        profile_text = f"""
👤 <b>Ваш профиль</b>

📝 Имя: {user_data[2]}
📱 Телефон: {user_data[3] or 'Не указан'}
📧 Email: {user_data[4] or 'Не указан'}
🌍 Язык: {user_data[5]}
📅 Регистрация: {user_data[7][:10]}
        """
        
        self.bot.send_message(chat_id, profile_text, self.keyboards.back_button())
    
    def _handle_category_selection(self, chat_id: int, text: str):
        """Обработка выбора категории"""
        # Извлекаем название категории из текста
        category_name = text.split(' ', 1)[1] if ' ' in text else text
        
        # Находим категорию
        categories = self.db.get_categories()
        selected_category = None
        
        for category in categories:
            if category[1] == category_name:
                selected_category = category
                break
        
        if not selected_category:
            self.bot.send_message(chat_id, "❌ Категория не найдена")
            return
        
        # Получаем товары категории
        products = self.db.get_products_by_category(selected_category[0])
        
        if not products:
            self.bot.send_message(
                chat_id, 
                f"📦 В категории '{category_name}' пока нет товаров",
                self.keyboards.back_button()
            )
            return
        
        category_text = f"📦 <b>{selected_category[3]} {selected_category[1]}</b>\n\n"
        category_text += f"Найдено товаров: {len(products)}\n\nВыберите товар:"
        
        self.bot.send_message(
            chat_id, 
            category_text, 
            self.keyboards.products_menu(products)
        )
    
    def _handle_product_selection(self, chat_id: int, text: str, user_id: int):
        """Обработка выбора товара"""
        # Извлекаем название товара из текста
        if ' - $' in text:
            product_name = text.split(' - $')[0].replace('🛍 ', '')
        else:
            product_name = text.replace('🛍 ', '')
        
        # Ищем товар
        products = self.db.search_products(product_name, 1)
        
        if not products:
            self.bot.send_message(chat_id, "❌ Товар не найден")
            return
        
        product = products[0]
        
        # Увеличиваем счетчик просмотров
        self.db.execute_query(
            'UPDATE products SET views = views + 1 WHERE id = ?',
            (product[0],)
        )
        
        # Показываем товар с выбором количества
        self._show_product_with_quantity(chat_id, product)
    
    def _show_product_with_quantity(self, chat_id: int, product: List):
        """Показ товара с выбором количества"""
        product_text = f"🛍 <b>{product[1]}</b>\n\n"
        
        if product[2]:
            product_text += f"📝 {product[2]}\n\n"
        
        product_text += f"💰 Цена: <b>{format_price(product[3])}</b>\n"
        product_text += f"📦 В наличии: {product[7]} шт.\n"
        product_text += f"👁 Просмотров: {product[8]}\n"
        product_text += f"🛒 Продано: {product[9]} шт."
        
        # Получаем отзывы
        reviews = self.db.get_product_reviews(product[0])
        if reviews:
            avg_rating = sum(review[0] for review in reviews) / len(reviews)
            product_text += f"\n⭐ Рейтинг: {avg_rating:.1f}/5 ({len(reviews)} отзывов)"
        
        product_text += f"\n\n<b>Выберите количество:</b>"
        
        # Клавиатура с выбором количества
        keyboard = self.keyboards.product_quantity_selection(product[0], product[7])
        
        if product[6]:  # Если есть изображение
            self.bot.send_photo(chat_id, product[6], product_text, keyboard)
        else:
            self.bot.send_message(chat_id, product_text, keyboard)
    
    def _handle_quantity_selection(self, chat_id: int, data: str, user_id: int, callback_query: Dict):
        """Обработка выбора количества"""
        parts = data.split('_')
        product_id = int(parts[1])
        quantity = int(parts[2])
        
        # Получаем товар
        product = self.db.get_product_by_id(product_id)
        if not product:
            return
        
        # Проверяем наличие
        if quantity > product[7]:
            self.bot.send_message(chat_id, f"❌ В наличии только {product[7]} шт.")
            return
        
        # Показываем подтверждение заказа
        confirm_text = f"""
🛍 <b>{product[1]}</b>

💰 Цена: {format_price(product[3])}
📦 Количество: {quantity} шт.
💳 <b>Итого: {format_price(product[3] * quantity)}</b>

Подтвердите заказ:
        """
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Заказать', 'callback_data': f'order_product_{product_id}_{quantity}'},
                    {'text': '🛒 В корзину', 'callback_data': f'add_to_cart_{product_id}_{quantity}'}
                ],
                [
                    {'text': '🔙 Назад к товару', 'callback_data': f'back_to_product_{product_id}'}
                ]
            ]
        }
        
        # Редактируем сообщение
        try:
            self.bot.edit_message_reply_markup(
                chat_id, 
                callback_query['message']['message_id'], 
                keyboard
            )
            self.bot.send_message(chat_id, confirm_text, keyboard)
        except:
            self.bot.send_message(chat_id, confirm_text, keyboard)
    
    def _handle_add_to_cart(self, chat_id: int, data: str, user_id: int):
        """Добавление товара в корзину"""
        parts = data.split('_')
        product_id = int(parts[3])
        quantity = int(parts[4]) if len(parts) > 4 else 1
        
        result = self.db.add_to_cart(user_id, product_id, quantity)
        
        if result:
            product = self.db.get_product_by_id(product_id)
            success_text = f"✅ <b>{product[1]}</b> ({quantity} шт.) добавлен в корзину!"
            
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🛒 Перейти в корзину', 'callback_data': 'goto_cart'},
                        {'text': '🛍 Продолжить покупки', 'callback_data': 'continue_shopping'}
                    ]
                ]
            }
            
            self.bot.send_message(chat_id, success_text, keyboard)
        else:
            self.bot.send_message(chat_id, "❌ Не удалось добавить товар в корзину")
    
    def _handle_order_product(self, chat_id: int, data: str, user_id: int):
        """Обработка быстрого заказа товара"""
        parts = data.split('_')
        product_id = int(parts[2])
        quantity = int(parts[3])
        
        product = self.db.get_product_by_id(product_id)
        if not product:
            return
        
        total_amount = product[3] * quantity
        
        # Создаем заказ
        order_id = self.db.create_order(
            user_id=user_id,
            total_amount=total_amount,
            delivery_address="Не указан",
            payment_method="cash"
        )
        
        if order_id:
            # Добавляем товар в заказ
            self.db.execute_query('''
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, product_id, quantity, product[3]))
            
            # Уменьшаем остаток
            self.db.execute_query('''
                UPDATE products SET stock = stock - ?, sales_count = sales_count + ?
                WHERE id = ?
            ''', (quantity, quantity, product_id))
            
            success_text = f"""
✅ <b>Заказ #{order_id} успешно создан!</b>

🛍 Товар: {product[1]}
📦 Количество: {quantity} шт.
💰 Сумма: {format_price(total_amount)}

📞 Мы свяжемся с вами в ближайшее время для подтверждения.

Спасибо за покупку! 🎉
            """
            
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🏠 Главное меню', 'callback_data': 'back_to_main'}
                    ]
                ]
            }
            
            self.bot.send_message(chat_id, success_text, keyboard)
            
            # Уведомляем админов
            if hasattr(self, 'notification_service'):
                self.notification_service.notify_order_created(order_id)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка создания заказа")
    
    def _search_products(self, chat_id: int, query: str):
        """Поиск товаров"""
        products = self.db.search_products(query, 10)
        
        if not products:
            not_found_text = f"""
🔍 <b>По запросу "{query}" ничего не найдено</b>

Попробуйте:
• Изменить запрос
• Использовать другие ключевые слова
• Просмотреть каталог по категориям
            """
            self.bot.send_message(chat_id, not_found_text, self.keyboards.back_button())
            return
        
        search_text = f"🔍 <b>Результаты поиска: '{query}'</b>\n\n"
        search_text += f"Найдено товаров: {len(products)}\n\n"
        
        for product in products[:5]:  # Показываем первые 5
            search_text += f"🛍 <b>{product[1]}</b>\n"
            search_text += f"💰 {format_price(product[3])}\n"
            search_text += f"📦 В наличии: {product[7]} шт.\n\n"
        
        self.bot.send_message(chat_id, search_text, self.keyboards.back_button())
    
    def _start_search(self, chat_id: int, telegram_id: int):
        """Начало поиска"""
        self.user_states[telegram_id] = {'state': 'search_products'}
        
        search_text = """
🔍 <b>Поиск товаров</b>

Введите название товара или ключевые слова для поиска:
        """
        
        keyboard = {
            'keyboard': [['🔙 Отмена']],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.bot.send_message(chat_id, search_text, keyboard)
    
    def _show_favorites(self, chat_id: int, user_id: int):
        """Показ избранных товаров"""
        favorites = self.db.get_user_favorites(user_id)
        
        if not favorites:
            empty_text = """
❤️ <b>Ваш список избранного пуст</b>

Добавляйте понравившиеся товары в избранное!
            """
            self.bot.send_message(chat_id, empty_text, self.keyboards.back_button())
            return
        
        favorites_text = "❤️ <b>Избранные товары</b>\n\n"
        
        for product in favorites[:10]:
            favorites_text += f"🛍 <b>{product[1]}</b>\n"
            favorites_text += f"💰 {format_price(product[3])}\n"
            favorites_text += f"📦 В наличии: {product[7]} шт.\n\n"
        
        self.bot.send_message(chat_id, favorites_text, self.keyboards.back_button())
    
    def _show_help(self, chat_id: int):
        """Показ справки"""
        help_text = """
ℹ️ <b>Справка по использованию бота</b>

🛍 <b>Каталог</b> - просмотр товаров по категориям
🛒 <b>Корзина</b> - ваши выбранные товары
📋 <b>Мои заказы</b> - история покупок
👤 <b>Профиль</b> - управление данными
🔍 <b>Поиск</b> - поиск товаров по названию
❤️ <b>Избранное</b> - сохраненные товары

<b>Как сделать заказ:</b>
1️⃣ Выберите товары в каталоге
2️⃣ Укажите количество
3️⃣ Нажмите "Заказать" или добавьте в корзину
4️⃣ Мы свяжемся с вами для подтверждения

❓ По вопросам обращайтесь к администратору.
        """
        
        self.bot.send_message(chat_id, help_text, self.keyboards.back_button())
    
    def _validate_email(self, email: str) -> bool:
        """Валидация email"""
        import re
        if not email or len(email) < 5:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_phone(self, phone: str) -> bool:
        """Валидация номера телефона"""
        import re
        if not phone:
            return False
        
        # Убираем все кроме цифр и +
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Проверяем различные форматы
        patterns = [
            r'^\+998\d{9}$',      # +998901234567
            r'^998\d{9}$',        # 998901234567
            r'^\d{9}$',           # 901234567
            r'^\+\d{10,15}$',     # Международный формат
        ]
        
        for pattern in patterns:
            if re.match(pattern, clean_phone):
                return True
        
        return False
    
    def _get_status_emoji(self, status: str) -> str:
        """Получение эмодзи для статуса"""
        emojis = {
            'pending': '⏳',
            'confirmed': '✅',
            'shipped': '🚚',
            'delivered': '📦',
            'cancelled': '❌'
        }
        return emojis.get(status, '❓')
    
    def _show_admin_menu(self, chat_id: int):
        """Показ админ меню"""
        admin_text = """
🛡 <b>Панель администратора</b>

Выберите раздел для управления:
        """
        
        self.bot.send_message(chat_id, admin_text, self.keyboards.admin_menu())
    
    def _send_registration_prompt(self, chat_id: int):
        """Приглашение к регистрации"""
        prompt_text = """
👋 <b>Добро пожаловать!</b>

Для использования бота необходимо зарегистрироваться.

Нажмите /start для начала регистрации.
        """
        
        self.bot.send_message(chat_id, prompt_text)