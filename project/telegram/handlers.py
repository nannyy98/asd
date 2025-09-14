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
            elif data.startswith('add_to_favorites_'):
                self._handle_add_to_favorites(chat_id, data, user_id)
            elif data.startswith('cart_'):
                self._handle_cart_action(chat_id, data, user_id)
            elif data.startswith('rate_'):
                self._handle_rating(chat_id, data, user_id)
            
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
        elif text.startswith('📱') or text.startswith('👕') or text.startswith('🏠'):
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
        if message['from'].get('last_name'):
            suggested_name += f" {message['from']['last_name']}"
        
        self.user_states[telegram_id] = {
            'state': 'registration_name',
            'data': {'suggested_name': suggested_name}
        }
        
        welcome_text = """
🛍 <b>Добро пожаловать в наш интернет-магазин!</b>

Для начала работы нужно пройти быструю регистрацию.

👤 <b>Как вас зовут?</b>
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
    
    def _handle_registration_name(self, message: Dict[str, Any], state_info: Dict):
        """Обработка ввода имени при регистрации"""
        telegram_id = message['from']['id']
        chat_id = message['chat']['id']
        name = sanitize_text(message['text'], 50)
        
        if len(name) < 2:
            self.bot.send_message(chat_id, "❌ Имя должно содержать минимум 2 символа")
            return
        
        state_info['data']['name'] = name
        state_info['state'] = 'registration_phone'
        
        phone_text = f"📱 <b>Отлично, {name}!</b>\n\nТеперь поделитесь номером телефона или пропустите этот шаг."
        
        keyboard = {
            'keyboard': [
                [{'text': '📱 Поделиться номером', 'request_contact': True}],
                ['⏭ Пропустить']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        self.bot.send_message(chat_id, phone_text, keyboard)
    
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
        
        cart_text = f"🛒 <b>Ваша корзина</b>\n\n"
        
        for item in cart_items:
            cart_text += f"🛍 <b>{item[1]}</b>\n"
            cart_text += f"💰 {format_price(item[2])} × {item[3]} = {format_price(item[2] * item[3])}\n\n"
        
        cart_text += f"💳 <b>Итого: {format_price(total)}</b>"
        
        self.bot.send_message(chat_id, cart_text, self.keyboards.cart_management(True))
    
    def _show_user_orders(self, chat_id: int, user_id: int):
        """Показ заказов пользователя"""
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            no_orders_text = """
📋 <b>У вас пока нет заказов</b>

Перейдите в каталог и сделайте первую покупку!
            """
            self.bot.send_message(chat_id, no_orders_text, self.keyboards.main_menu())
            return
        
        orders_text = "📋 <b>Ваши заказы</b>\n\n"
        
        for order in orders[:10]:  # Показываем последние 10
            status_emoji = self._get_status_emoji(order[3])
            orders_text += f"{status_emoji} Заказ #{order[0]} - {format_price(order[2])}\n"
            orders_text += f"📅 {order[7][:16]}\n\n"
        
        self.bot.send_message(chat_id, orders_text, self.keyboards.back_button())
    
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
        
        # Показываем товар
        self._show_product_details(chat_id, product)
    
    def _show_product_details(self, chat_id: int, product: List):
        """Показ деталей товара"""
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
        
        keyboard = self.keyboards.product_actions(product[0])
        
        if product[6]:  # Если есть изображение
            self.bot.send_photo(chat_id, product[6], product_text, keyboard)
        else:
            self.bot.send_message(chat_id, product_text, keyboard)
    
    def _handle_add_to_cart(self, chat_id: int, data: str, user_id: int):
        """Добавление товара в корзину"""
        product_id = int(data.split('_')[-1])
        
        result = self.db.add_to_cart(user_id, product_id, 1)
        
        if result:
            product = self.db.get_product_by_id(product_id)
            success_text = f"✅ <b>{product[1]}</b> добавлен в корзину!"
            
            # Показываем кнопки для дальнейших действий
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
            self.bot.send_message(chat_id, not_found_text, self.keyboards.main_menu())
            return
        
        search_text = f"🔍 <b>Результаты поиска: '{query}'</b>\n\n"
        search_text += f"Найдено товаров: {len(products)}\n\n"
        
        for product in products[:5]:  # Показываем первые 5
            search_text += f"🛍 <b>{product[1]}</b>\n"
            search_text += f"💰 {format_price(product[3])}\n"
            search_text += f"📦 В наличии: {product[7]} шт.\n\n"
        
        self.bot.send_message(chat_id, search_text, self.keyboards.back_button())
    
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
2️⃣ Добавьте их в корзину
3️⃣ Оформите заказ
4️⃣ Укажите адрес и способ оплаты

❓ По вопросам обращайтесь к администратору.
        """
        
        self.bot.send_message(chat_id, help_text, self.keyboards.main_menu())
    
    def _validate_email(self, email: str) -> bool:
        """Валидация email"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
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