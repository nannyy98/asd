"""
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
            
            # Обрабатываем навигационные кнопки ПЕРВЫМИ
            if text in ['🏠 Главная', '🏠 Bosh sahifa']:
                self.send_main_menu(chat_id, language, user_data[0])
                return
            elif text in ['🔙 Назад', '🔙 Orqaga']:
                self.handle_back_button(chat_id, telegram_id, language)
                return
            elif text in ['🔙 К категориям', '🔙 Kategoriyalarga']:
                self.show_catalog(chat_id, language)
                return
            elif text in ['🔙 Главная', '🔙 Bosh sahifa']:
                self.send_main_menu(chat_id, language, user_data[0])
                return
            
            # Основные команды
            if text == '/start':
                self.send_welcome_message(chat_id, language, user_data[0])
            elif text == '/help':
                self.send_help_message(chat_id, language)
            elif text in ['🛍 Каталог', '🛍 Katalog']:
                self.show_catalog(chat_id, language)
            elif text in ['🛒 Корзина', '🛒 Savat']:
                self.show_cart(chat_id, user_id, language)
            elif text in ['📋 Мои заказы', '📋 Mening buyurtmalarim']:
                self.show_user_orders(chat_id, user_id, language)
            elif text in ['👤 Профиль', '👤 Profil']:
                self.show_user_profile(chat_id, user_id, language)
            elif text in ['🔍 Поиск', '🔍 Qidiruv']:
                self.start_search(chat_id, language)
            elif text in ['ℹ️ Помощь', 'ℹ️ Yordam']:
                self.send_help_message(chat_id, language)
            elif text in ['⭐ Программа лояльности', '⭐ Sadoqat dasturi']:
                self.show_loyalty_program(chat_id, user_id, language)
            elif text in ['🎁 Промокоды', '🎁 Promokodlar']:
                self.show_promo_codes(chat_id, user_id, language)
            elif text.startswith('📱 ') or text.startswith('👕 ') or text.startswith('🏠 ') or text.startswith('⚽ ') or text.startswith('💄 ') or text.startswith('📚 '):
                self.handle_category_selection(message, user_id, language)
            elif text.startswith('🛍 '):
                self.handle_product_selection(message, user_id, language)
            elif text.startswith('📦 Оформить заказ') or text.startswith('📦 Buyurtma berish'):
                self.start_order_process(chat_id, user_id, language)
            elif text.startswith('🗑 Очистить корзину') or text.startswith('🗑 Savatni tozalash'):
                self.clear_user_cart(chat_id, user_id, language)
            elif text.startswith('➕ Добавить товары') or text.startswith('➕ Mahsulot qo\'shish'):
                self.show_catalog(chat_id, language)
            elif text.startswith('🛍 Перейти в каталог') or text.startswith('🛍 Katalogga o\'tish'):
                self.show_catalog(chat_id, language)
            else:
                # Проверяем состояние пользователя
                state = self.user_states.get(telegram_id, '')
                if state.startswith('registration_'):
                    self.handle_registration_step(message)
                elif state == 'searching':
                    self.handle_search_query(message, user_id, language)
                elif state == 'ordering':
                    self.handle_order_process(message, user_id, language)
                elif state.startswith('viewing_category_'):
                    self.handle_subcategory_selection(message, user_id, language)
                elif state.startswith('viewing_subcategory_'):
                    self.handle_product_from_subcategory(message, user_id, language)
                else:
                    self.send_unknown_command(chat_id, language)
                    
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            self.bot.send_message(chat_id, "❌ Произошла ошибка. Попробуйте позже.")
    
    def send_main_menu(self, chat_id, language, user_data):
        """Отправка главного меню"""
        # Очищаем состояние пользователя
        telegram_id = user_data[1]
        if telegram_id in self.user_states:
            del self.user_states[telegram_id]
        
        welcome_text = t('welcome_back', language=language)
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def handle_back_button(self, chat_id, telegram_id, language):
        """Обработка кнопки Назад"""
        current_state = self.user_states.get(telegram_id, '')
        
        if current_state.startswith('viewing_category_'):
            # Возврат к каталогу
            self.show_catalog(chat_id, language)
        elif current_state.startswith('viewing_subcategory_'):
            # Возврат к категории
            category_id = current_state.split('_')[2]
            self.show_category_products(chat_id, int(category_id), language, telegram_id)
        elif current_state.startswith('viewing_product_'):
            # Возврат к подкатегории или категории
            self.show_catalog(chat_id, language)
        elif current_state == 'searching':
            # Возврат из поиска
            del self.user_states[telegram_id]
            self.send_main_menu(chat_id, language, self.get_user_data(telegram_id))
        elif current_state == 'ordering':
            # Возврат из оформления заказа
            del self.user_states[telegram_id]
            user_data = self.get_user_data(telegram_id)
            user_id = user_data[0]
            self.show_cart(chat_id, user_id, language)
        else:
            # По умолчанию - главное меню
            user_data = self.get_user_data(telegram_id)
            self.send_main_menu(chat_id, language, user_data)
    
    def get_user_data(self, telegram_id):
        """Получение данных пользователя"""
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        return user_data[0] if user_data else None
    
    def start_registration(self, message):
        """Начало регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Предлагаем имя из Telegram
        suggested_name = message['from'].get('first_name', '')
        if message['from'].get('last_name'):
            suggested_name += f" {message['from']['last_name']}"
        
        self.user_states[telegram_id] = 'registration_name'
        
        welcome_text = "🛍 <b>Добро пожаловать в наш интернет-магазин!</b>\n\n"
        welcome_text += "Для начала работы пройдите быструю регистрацию.\n\n"
        welcome_text += "👤 Как вас зовут?"
        
        keyboard = create_registration_keyboard('name', suggested_name)
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def handle_registration_step(self, message):
        """Обработка шагов регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        state = self.user_states.get(telegram_id, '')
        
        if text == '❌ Отмена':
            del self.user_states[telegram_id]
            self.bot.send_message(chat_id, "Регистрация отменена.")
            return
        
        if state == 'registration_name':
            if not hasattr(self, 'registration_data'):
                self.registration_data = {}
            
            self.user_states[telegram_id] = 'registration_phone'
            self.registration_data[telegram_id] = {'name': text}
            
            phone_text = "📱 Поделитесь номером телефона или пропустите этот шаг"
            keyboard = create_registration_keyboard('phone')
            self.bot.send_message(chat_id, phone_text, keyboard)
            
        elif state == 'registration_phone':
            phone = None
            if 'contact' in message:
                phone = message['contact']['phone_number']
            elif text != '⏭ Пропустить':
                phone = text
            
            if not hasattr(self, 'registration_data'):
                self.registration_data = {}
            if telegram_id not in self.registration_data:
                self.registration_data[telegram_id] = {'name': 'Пользователь'}
            
            self.registration_data[telegram_id]['phone'] = phone
            self.user_states[telegram_id] = 'registration_language'
            
            lang_text = "🌍 Выберите язык / Tilni tanlang"
            keyboard = create_registration_keyboard('language')
            self.bot.send_message(chat_id, lang_text, keyboard)
            
        elif state == 'registration_language':
            language = 'ru'
            if text == '🇺🇿 O\'zbekcha':
                language = 'uz'
            
            # Создаем пользователя
            reg_data = self.registration_data.get(telegram_id, {'name': 'Пользователь'})
            user_id = self.db.add_user(
                telegram_id,
                reg_data['name'],
                reg_data.get('phone'),
                None,
                language
            )
            
            if user_id:
                del self.user_states[telegram_id]
                if hasattr(self, 'registration_data') and telegram_id in self.registration_data:
                    del self.registration_data[telegram_id]
                
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
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, help_text, keyboard)
    
    def show_catalog(self, chat_id, language):
        """Показ каталога"""
        try:
            categories = self.db.get_categories()
            print(f"DEBUG: Получено категорий: {len(categories) if categories else 0}")
            
            if categories:
                catalog_text = "🛍 <b>Каталог товаров</b>\n\nВыберите категорию:"
                keyboard = create_categories_keyboard(categories)
                self.bot.send_message(chat_id, catalog_text, keyboard)
            else:
                error_text = "❌ Каталог временно недоступен\n\n💡 Попробуйте позже или обратитесь к администратору"
                keyboard = create_main_keyboard()
                self.bot.send_message(chat_id, error_text, keyboard)
        except Exception as e:
            print(f"DEBUG: Ошибка показа каталога: {e}")
            error_text = "❌ Ошибка загрузки каталога\n\n🔄 Попробуйте еще раз"
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, error_text, keyboard)
    
    def handle_category_selection(self, message, user_id, language):
        """Обработка выбора категории"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        # Извлекаем название категории из текста кнопки
        # Убираем эмодзи и получаем название категории
        if ' ' in text:
            category_name = text.split(' ', 1)[1].strip()
        else:
            category_name = text.strip()
        
        # Находим категорию по названию
        categories = self.db.get_categories()
        selected_category = None
        
        for category in categories:
            if category[1].strip() == category_name:
                selected_category = category
                break
        
        if selected_category:
            category_id = selected_category[0]
            self.user_states[telegram_id] = f'viewing_category_{category_id}'
            self.show_category_products(chat_id, category_id, language, telegram_id)
        else:
            print(f"DEBUG: Категория не найдена. Искали: '{category_name}', Доступные: {[cat[1] for cat in categories]}")
            self.bot.send_message(chat_id, "❌ Категория не найдена")
            # Показываем каталог заново
            self.show_catalog(chat_id, language)
    
    def show_category_products(self, chat_id, category_id, language, telegram_id):
        """Показ товаров категории через подкатегории"""
        try:
            subcategories = self.db.get_products_by_category(category_id)
            print(f"DEBUG: Подкатегории для категории {category_id}: {subcategories}")
        except Exception as e:
            print(f"DEBUG: Ошибка получения подкатегорий: {e}")
            subcategories = []
        
        if subcategories:
            try:
                category_result = self.db.execute_query(
                    'SELECT name FROM categories WHERE id = ?', (category_id,)
                )
                category_name = category_result[0][0] if category_result else "Категория"
            except Exception as e:
                print(f"DEBUG: Ошибка получения названия категории: {e}")
                category_name = "Категория"
            
            subcategory_text = f"📂 <b>{category_name}</b>\n\nВыберите бренд или подкатегорию:"
            keyboard = create_subcategories_keyboard(subcategories)
            self.bot.send_message(chat_id, subcategory_text, keyboard)
        else:
            # Если нет подкатегорий, показываем товары напрямую
            try:
                products = self.db.execute_query('''
                    SELECT * FROM products 
                    WHERE category_id = ? AND is_active = 1 
                    ORDER BY name LIMIT 10
                ''', (category_id,))
                print(f"DEBUG: Товары в категории {category_id}: {len(products) if products else 0}")
            except Exception as e:
                print(f"DEBUG: Ошибка получения товаров: {e}")
                products = []
            
            if products:
                self.show_products_list(chat_id, products, language)
            else:
                no_products_text = "❌ В этой категории пока нет товаров\n\n🔙 Вернитесь в каталог для выбора другой категории"
                keyboard = create_back_keyboard()
                self.bot.send_message(chat_id, no_products_text, keyboard)
    
    def handle_subcategory_selection(self, message, user_id, language):
        """Обработка выбора подкатегории"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        # Извлекаем название подкатегории
        if ' ' in text:
            subcategory_name = text.split(' ', 1)[1].strip()
        else:
            subcategory_name = text.strip()
        
        print(f"DEBUG: Ищем подкатегорию: '{subcategory_name}'")
        
        # Находим подкатегорию
        try:
            subcategory = self.db.execute_query(
                'SELECT id FROM subcategories WHERE name = ?', (subcategory_name,)
            )
            print(f"DEBUG: Результат поиска подкатегории: {subcategory}")
        except Exception as e:
            print(f"DEBUG: Ошибка поиска подкатегории: {e}")
            subcategory = None
        
        if subcategory:
            subcategory_id = subcategory[0][0]
            self.user_states[telegram_id] = f'viewing_subcategory_{subcategory_id}'
            
            # Получаем товары подкатегории
            try:
                products = self.db.get_products_by_subcategory(subcategory_id)
                print(f"DEBUG: Товары в подкатегории {subcategory_id}: {len(products) if products else 0}")
            except Exception as e:
                print(f"DEBUG: Ошибка получения товаров подкатегории: {e}")
                products = []
            
            if products:
                self.show_products_list(chat_id, products, language)
            else:
                no_products_text = "❌ В этой подкатегории пока нет товаров\n\n🔙 Выберите другую подкатегорию"
                keyboard = create_back_keyboard()
                self.bot.send_message(chat_id, no_products_text, keyboard)
        else:
            print(f"DEBUG: Подкатегория '{subcategory_name}' не найдена")
            self.bot.send_message(chat_id, "❌ Подкатегория не найдена")
            # Возвращаем к каталогу
            self.show_catalog(chat_id, language)
    
    def show_products_list(self, chat_id, products, language):
        """Показ списка товаров"""
        if not products:
            no_products_text = "❌ Товары не найдены\n\n🔍 Попробуйте поиск или выберите другую категорию"
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, no_products_text, keyboard)
            return
        
        try:
            products_text = f"🛍 <b>Найдено товаров: {len(products)}</b>\n\n"
            
            # Показываем список товаров кнопками
            products_keyboard = []
            for product in products[:10]:  # Показываем до 10 товаров
                try:
                    name = product[1] if len(product) > 1 else 'Товар'
                    price = product[3] if len(product) > 3 else 0
                    products_keyboard.append([f"🛍 {name} - ${price:.2f}"])
                except Exception as e:
                    print(f"DEBUG: Ошибка обработки товара: {e}")
                    continue
            
            products_keyboard.append(['🔙 Назад', '🏠 Главная'])
            
            keyboard = {
                'keyboard': products_keyboard,
                'resize_keyboard': True,
                'one_time_keyboard': False
            }
            
            self.bot.send_message(chat_id, products_text, keyboard)
            
        except Exception as e:
            print(f"DEBUG: Ошибка показа списка товаров: {e}")
            error_text = "❌ Ошибка отображения товаров"
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, error_text, keyboard)
    
    def show_product_card(self, chat_id, product, language):
        """Показ карточки товара"""
        product_id = product[0]
        name = product[1]
        description = product[2] or "Описание отсутствует"
        price = product[3]
        image_url = product[6] if len(product) > 6 else None
        stock = product[7] if len(product) > 7 else 0
        
        # Увеличиваем счетчик просмотров
        self.db.increment_product_views(product_id)
        
        card_text = f"<b>{name}</b>\n\n"
        card_text += f"{description[:200]}{'...' if len(description) > 200 else ''}\n\n"
        card_text += f"💰 Цена: <b>{format_price(price)}</b>\n"
        card_text += f"📦 В наличии: {stock} шт."
        
        keyboard = create_product_inline_keyboard(product_id)
        
        if image_url:
            self.bot.send_photo(chat_id, image_url, card_text, keyboard)
        else:
            self.bot.send_message(chat_id, card_text, keyboard)
    
    def handle_product_selection(self, message, user_id, language):
        """Обработка выбора товара из списка"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        # Извлекаем название товара из текста кнопки
        if text.startswith('🛍 '):
            product_info = text[2:]  # Убираем эмодзи
            product_name = product_info.split(' - ')[0].strip()
            
            # Находим товар по названию
            product = self.db.execute_query(
                'SELECT * FROM products WHERE name = ? AND is_active = 1',
                (product_name,)
            )
            
            if product:
                self.show_product_card(chat_id, product[0], language)
            else:
                self.bot.send_message(chat_id, "❌ Товар не найден")
    
    def show_cart(self, chat_id, user_id, language):
        """Показ корзины"""
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            empty_text = t('empty_cart', language=language)
            keyboard = create_cart_keyboard(False)
            self.bot.send_message(chat_id, empty_text, keyboard)
            return
        
        cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
        total = 0
        
        for item in cart_items:
            item_total = item[2] * item[3]
            total += item_total
            cart_text += f"• {item[1]} × {item[3]} = {format_price(item_total)}\n"
        
        cart_text += f"\n💰 <b>Итого: {format_price(total)}</b>"
        
        keyboard = create_cart_keyboard(True)
        self.bot.send_message(chat_id, cart_text, keyboard)
    
    def clear_user_cart(self, chat_id, user_id, language):
        """Очистка корзины пользователя"""
        result = self.db.clear_cart(user_id)
        if result is not None:
            self.bot.send_message(chat_id, "✅ Корзина очищена")
            # Показываем пустую корзину
            self.show_cart(chat_id, user_id, language)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка очистки корзины")
    
    def start_order_process(self, chat_id, user_id, language):
        """Начало процесса оформления заказа"""
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            self.bot.send_message(chat_id, "❌ Корзина пуста")
            return
        
        total = calculate_cart_total(cart_items)
        
        order_text = f"📦 <b>Оформление заказа</b>\n\n"
        order_text += f"💰 Сумма заказа: {format_price(total)}\n\n"
        order_text += f"📍 Укажите адрес доставки:"
        
        # Устанавливаем состояние
        telegram_id = message['from']['id']
        self.user_states[telegram_id] = 'ordering_address'
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, order_text, keyboard)
    
    def handle_order_process(self, message, user_id, language):
        """Обработка процесса заказа"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        state = self.user_states.get(telegram_id, '')
        
        if state == 'ordering_address':
            # Сохраняем адрес и переходим к способу оплаты
            if not hasattr(self, 'order_data'):
                self.order_data = {}
            self.order_data[telegram_id] = {'address': text}
            self.user_states[telegram_id] = 'ordering_payment'
            
            payment_text = "💳 Выберите способ оплаты:"
            keyboard = create_payment_methods_keyboard(language)
            self.bot.send_message(chat_id, payment_text, keyboard)
            
        elif state == 'ordering_payment':
            # Создаем заказ
            order_data = self.order_data.get(telegram_id, {})
            cart_items = self.db.get_cart_items(user_id)
            total = calculate_cart_total(cart_items)
            
            # Создаем заказ
            order_id = self.db.create_order(
                user_id, total, order_data.get('address', ''), text
            )
            
            if order_id:
                # Добавляем товары в заказ
                self.db.add_order_items(order_id, cart_items)
                
                # Очищаем корзину
                self.db.clear_cart(user_id)
                
                # Очищаем состояние
                del self.user_states[telegram_id]
                if hasattr(self, 'order_data') and telegram_id in self.order_data:
                    del self.order_data[telegram_id]
                
                # Уведомляем о успешном заказе
                success_text = f"✅ <b>Заказ #{order_id} успешно оформлен!</b>\n\n"
                success_text += f"💰 Сумма: {format_price(total)}\n"
                success_text += f"📞 Мы свяжемся с вами в ближайшее время для подтверждения.\n\n"
                success_text += f"Спасибо за покупку! 🎉"
                
                keyboard = create_main_keyboard()
                self.bot.send_message(chat_id, success_text, keyboard)
                
                # Уведомляем админов
                if self.notification_manager:
                    self.notification_manager.send_order_notification_to_admins(order_id)
            else:
                self.bot.send_message(chat_id, "❌ Ошибка создания заказа")
    
    def show_user_orders(self, chat_id, user_id, language):
        """Показ заказов пользователя"""
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            no_orders_text = "📋 У вас пока нет заказов\n\n🛍 Перейдите в каталог, чтобы сделать первый заказ!"
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, no_orders_text, keyboard)
            return
        
        orders_text = "📋 <b>Ваши заказы:</b>\n\n"
        
        for order in orders[:10]:  # Показываем последние 10
            status_emoji = get_order_status_emoji(order[3])
            status_text = get_order_status_text(order[3])
            orders_text += f"{status_emoji} Заказ #{order[0]} - {format_price(order[2])}\n"
            orders_text += f"📊 Статус: {status_text}\n"
            orders_text += f"📅 {format_date(order[7])}\n\n"
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, orders_text, keyboard)
    
    def show_user_profile(self, chat_id, user_id, language):
        """Показ профиля пользователя"""
        user = self.db.execute_query('SELECT * FROM users WHERE id = ?', (user_id,))[0]
        
        profile_text = f"👤 <b>Ваш профиль</b>\n\n"
        profile_text += f"📝 Имя: {user[2]}\n"
        if user[3]:
            profile_text += f"📱 Телефон: {user[3]}\n"
        if user[4]:
            profile_text += f"📧 Email: {user[4]}\n"
        profile_text += f"🌍 Язык: {'Русский' if user[5] == 'ru' else 'O\'zbekcha'}\n"
        profile_text += f"📅 Регистрация: {format_date(user[7])}"
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, profile_text, keyboard)
    
    def start_search(self, chat_id, language):
        """Начало поиска"""
        search_text = "🔍 <b>Поиск товаров</b>\n\nВведите название товара для поиска:"
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, search_text, keyboard)
        
        # Устанавливаем состояние поиска
        telegram_id = chat_id  # Предполагаем что chat_id = telegram_id для личных чатов
        self.user_states[telegram_id] = 'searching'
    
    def handle_search_query(self, message, user_id, language):
        """Обработка поискового запроса"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        query = message.get('text', '')
        
        # Очищаем состояние поиска
        if telegram_id in self.user_states:
            del self.user_states[telegram_id]
        
        # Ищем товары
        products = self.db.search_products(query, 5)
        
        if products:
            search_result_text = f"🔍 <b>Результаты поиска:</b> \"{query}\"\n\n"
            search_result_text += f"Найдено {len(products)} товар(ов):"
            
            self.bot.send_message(chat_id, search_result_text)
            
            # Показываем найденные товары
            for product in products:
                self.show_product_card(chat_id, product, language)
        else:
            not_found_text = f"❌ По запросу \"{query}\" ничего не найдено\n\n"
            not_found_text += "💡 Попробуйте:\n"
            not_found_text += "• Изменить запрос\n"
            not_found_text += "• Использовать другие ключевые слова\n"
            not_found_text += "• Просмотреть каталог"
            
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, not_found_text, keyboard)
    
    def show_loyalty_program(self, chat_id, user_id, language):
        """Показ программы лояльности"""
        loyalty_data = self.db.get_user_loyalty_points(user_id)
        
        loyalty_text = f"⭐ <b>Программа лояльности</b>\n\n"
        loyalty_text += f"💎 Ваш уровень: <b>{loyalty_data[4]}</b>\n"
        loyalty_text += f"🏆 Баллов: <b>{loyalty_data[2]}</b>\n"
        loyalty_text += f"📊 Всего заработано: {loyalty_data[3]}\n\n"
        loyalty_text += f"🎁 Используйте баллы для получения скидок!"
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, loyalty_text, keyboard)
    
    def show_promo_codes(self, chat_id, user_id, language):
        """Показ доступных промокодов"""
        try:
            from promotions import PromotionManager
            promo_manager = PromotionManager(self.db)
            available_promos = promo_manager.get_user_available_promos(user_id)
            
            if available_promos:
                promo_text = f"🎁 <b>Доступные промокоды:</b>\n\n"
                
                for promo in available_promos[:5]:
                    promo_text += f"🏷 <code>{promo[1]}</code>\n"
                    promo_text += f"💰 Скидка: {promo[3]}{'%' if promo[2] == 'percentage' else '$'}\n"
                    if promo[4] > 0:
                        promo_text += f"📊 Минимальная сумма: {format_price(promo[4])}\n"
                    promo_text += f"📝 {promo[7]}\n\n"
            else:
                promo_text = "🎁 <b>Промокоды</b>\n\nК сожалению, сейчас нет доступных промокодов.\n\n💡 Следите за новостями!"
        except ImportError:
            promo_text = "🎁 <b>Промокоды</b>\n\nСистема промокодов временно недоступна."
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, promo_text, keyboard)
    
    def handle_callback_query(self, callback_query):
        """Обработка callback запросов"""
        try:
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            message_id = callback_query['message']['message_id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            language = user_data[0][5]
            
            if data.startswith('add_to_cart_'):
                product_id = int(data.split('_')[3])
                self.add_product_to_cart(chat_id, user_id, product_id, language)
            elif data.startswith('add_to_favorites_'):
                product_id = int(data.split('_')[3])
                self.add_to_favorites(chat_id, user_id, product_id, language)
            elif data.startswith('reviews_'):
                product_id = int(data.split('_')[1])
                self.show_product_reviews(chat_id, product_id, language)
            elif data.startswith('rate_product_'):
                product_id = int(data.split('_')[2])
                self.show_rating_keyboard(chat_id, product_id, message_id)
            elif data.startswith('rate_'):
                parts = data.split('_')
                product_id = int(parts[1])
                rating = int(parts[2])
                self.save_product_rating(chat_id, user_id, product_id, rating, language)
            elif data.startswith('cart_increase_'):
                cart_item_id = int(data.split('_')[2])
                self.update_cart_item_quantity(chat_id, user_id, cart_item_id, 1, language)
            elif data.startswith('cart_decrease_'):
                cart_item_id = int(data.split('_')[2])
                self.update_cart_item_quantity(chat_id, user_id, cart_item_id, -1, language)
            elif data.startswith('cart_remove_'):
                cart_item_id = int(data.split('_')[2])
                self.remove_cart_item(chat_id, user_id, cart_item_id, language)
            elif data == 'cancel_rating':
                self.bot.send_message(chat_id, "❌ Оценка отменена")
                
        except Exception as e:
            print(f"Ошибка обработки callback: {e}")
            self.bot.send_message(chat_id, "❌ Произошла ошибка")
    
    def add_product_to_cart(self, chat_id, user_id, product_id, language):
        """Добавление товара в корзину"""
        result = self.db.add_to_cart(user_id, product_id, 1)
        
        if result:
            self.bot.send_message(chat_id, "✅ Товар добавлен в корзину!")
        else:
            self.bot.send_message(chat_id, "❌ Товар недоступен или закончился")
    
    def add_to_favorites(self, chat_id, user_id, product_id, language):
        """Добавление в избранное"""
        result = self.db.add_to_favorites(user_id, product_id)
        
        if result:
            self.bot.send_message(chat_id, "❤️ Товар добавлен в избранное!")
        else:
            self.bot.send_message(chat_id, "❌ Ошибка добавления в избранное")
    
    def show_product_reviews(self, chat_id, product_id, language):
        """Показ отзывов о товаре"""
        reviews = self.db.get_product_reviews(product_id)
        
        if reviews:
            reviews_text = "⭐ <b>Отзывы о товаре:</b>\n\n"
            
            for review in reviews[:5]:
                stars = '⭐' * review[0]
                reviews_text += f"{stars} <b>Оценка: {review[0]}/5</b>\n"
                if review[1]:
                    reviews_text += f"💭 \"{review[1]}\"\n"
                reviews_text += f"👤 {review[3]} • {format_date(review[2])}\n\n"
        else:
            reviews_text = "⭐ <b>Отзывы о товаре</b>\n\nПока нет отзывов об этом товаре.\n\n💡 Станьте первым, кто оставит отзыв!"
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, reviews_text, keyboard)
    
    def show_rating_keyboard(self, chat_id, product_id, message_id):
        """Показ клавиатуры для оценки"""
        rating_text = "⭐ Оцените товар от 1 до 5 звезд:"
        keyboard = create_rating_keyboard(product_id)
        
        # Редактируем сообщение с новой клавиатурой
        self.bot.edit_message_reply_markup(chat_id, message_id, keyboard)
        self.bot.send_message(chat_id, rating_text)
    
    def save_product_rating(self, chat_id, user_id, product_id, rating, language):
        """Сохранение оценки товара"""
        result = self.db.add_review(user_id, product_id, rating, "")
        
        if result:
            self.bot.send_message(chat_id, f"✅ Спасибо за оценку! Вы поставили {rating} звезд.")
        else:
            self.bot.send_message(chat_id, "❌ Ошибка сохранения оценки")
    
    def update_cart_item_quantity(self, chat_id, user_id, cart_item_id, change, language):
        """Обновление количества товара в корзине"""
        # Получаем текущее количество
        cart_item = self.db.execute_query(
            'SELECT quantity FROM cart WHERE id = ?', (cart_item_id,)
        )
        
        if cart_item:
            new_quantity = cart_item[0][0] + change
            result = self.db.update_cart_quantity(cart_item_id, new_quantity)
            
            if result is not None:
                if new_quantity > 0:
                    self.bot.send_message(chat_id, f"✅ Количество обновлено: {new_quantity} шт.")
                else:
                    self.bot.send_message(chat_id, "✅ Товар удален из корзины")
                
                # Показываем обновленную корзину
                self.show_cart(chat_id, user_id, language)
            else:
                self.bot.send_message(chat_id, "❌ Ошибка обновления корзины")
    
    def remove_cart_item(self, chat_id, user_id, cart_item_id, language):
        """Удаление товара из корзины"""
        result = self.db.remove_from_cart(cart_item_id)
        
        if result is not None:
            self.bot.send_message(chat_id, "✅ Товар удален из корзины")
            # Показываем обновленную корзину
            self.show_cart(chat_id, user_id, language)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка удаления товара")
    
    def send_unknown_command(self, chat_id, language):
        """Отправка сообщения о неизвестной команде"""
        unknown_text = "❓ Команда не распознана.\n\n💡 Используйте кнопки меню ниже для навигации:"
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, unknown_text, keyboard)