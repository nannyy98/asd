"""
Система постов для телеграм-бота (только ручное управление)
"""

import threading
import time
from datetime import datetime
from utils import format_date
from logger import logger

class ScheduledPostsManager:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.channel_id = "-1002566537425"  # ID канала для постов
        self.post_templates = self.load_post_templates()
        # НЕ запускаем автоматический планировщик
        logger.info("✅ Система постов инициализирована (только ручное управление)")
    
    def load_post_templates(self):
        """Загрузка шаблонов постов"""
        return {
            'morning_greeting': {
                'title': 'Доброе утро! 🌅',
                'content': '''🌅 <b>Доброе утро, дорогие покупатели!</b>

☕ Начните день с приятных покупок в нашем магазине!

🛍 <b>Сегодня для вас:</b>
• Новинки в каталоге
• Специальные предложения
• Быстрая доставка

💫 Желаем продуктивного дня!''',
                'image': 'https://images.pexels.com/photos/1002703/pexels-photo-1002703.jpeg'
            },
            
            'afternoon_promo': {
                'title': 'Дневные предложения! ☀️',
                'content': '''☀️ <b>Добрый день!</b>

🔥 <b>ГОРЯЧИЕ ПРЕДЛОЖЕНИЯ ДНЯ:</b>
• Скидки до 30% на популярные товары
• Бесплатная доставка от $50
• Новинки по специальным ценам

⏰ Предложения действуют до конца дня!
🛒 Не упустите возможность!''',
                'image': 'https://images.pexels.com/photos/1303081/pexels-photo-1303081.jpeg'
            },
            
            'evening_recommendations': {
                'title': 'Вечерние рекомендации 🌆',
                'content': '''🌆 <b>Добрый вечер!</b>

💡 <b>Специально для вас подобрали:</b>
• Товары по вашим интересам
• Популярные новинки
• Эксклюзивные предложения

🎁 Оформите заказ сегодня и получите:
• Бесплатную доставку
• Дополнительную скидку 5%

🌙 Приятного вечера и удачных покупок!''',
                'image': 'https://images.pexels.com/photos/230544/pexels-photo-230544.jpeg'
            },
            
            'special_promotion': {
                'title': 'Специальная акция! 🎁',
                'content': '''🎁 <b>СПЕЦИАЛЬНАЯ АКЦИЯ!</b>

🔥 <b>Только сегодня:</b>
• Скидка 25% на ВСЕ товары
• Промокод: SPECIAL25
• Бесплатная доставка

⚡ <b>Успейте до полуночи!</b>
🛍 Количество товаров ограничено!

💰 Экономьте до $200 на покупках!''',
                'image': 'https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg'
            },
            
            'weekend_sale': {
                'title': 'Выходные скидки! 🎉',
                'content': '''🎉 <b>ВЫХОДНЫЕ СКИДКИ!</b>

🛍 <b>Весь уикенд действуют:</b>
• Скидки до 40% на хиты продаж
• Дополнительная скидка 10% при покупке от $100
• Подарок к каждому заказу

🎯 <b>Специальные предложения:</b>
• Электроника -30%
• Одежда -25% 
• Товары для дома -35%

⏰ До воскресенья включительно!''',
                'image': 'https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg'
            },
            
            'new_arrivals': {
                'title': 'Новинки недели! ✨',
                'content': '''✨ <b>НОВИНКИ НЕДЕЛИ!</b>

🆕 <b>Встречайте свежие поступления:</b>
• Последние модели смартфонов
• Трендовая одежда сезона
• Инновационные гаджеты

🎁 <b>Для первых покупателей:</b>
• Скидка 15% на новинки
• Приоритетная доставка
• Гарантия качества

🚀 Будьте первыми, кто оценит новинку!''',
                'image': 'https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg'
            },
            
            'flash_sale': {
                'title': 'Флеш-распродажа! ⚡',
                'content': '''⚡ <b>ФЛЕШ-РАСПРОДАЖА!</b>

🔥 <b>ТОЛЬКО 24 ЧАСА:</b>
• Скидка 30% на ВСЕ товары
• Промокод: FLASH30
• Количество ограничено!

⏰ <b>Торопитесь!</b>
До конца акции осталось мало времени!

💨 Самые быстрые получат лучшие товары!
🛒 Заказывайте прямо сейчас!''',
                'image': 'https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg'
            },
            
            'birthday_greeting': {
                'title': 'С Днем Рождения! 🎂',
                'content': '''🎂 <b>С ДНЕМ РОЖДЕНИЯ!</b>

🎉 Сегодня особенный день!

🎁 <b>Праздничные подарки:</b>
• Скидка 20% на все товары
• Промокод: BIRTHDAY20
• Бесплатная доставка
• Подарочная упаковка

🥳 Пусть этот день будет наполнен радостью!

💝 Выберите себе подарок в нашем каталоге!''',
                'image': 'https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg'
            }
        }
    
    def send_template_post(self, template_key):
        """Отправка поста по шаблону (ТОЛЬКО РУЧНАЯ)"""
        try:
            template = self.post_templates.get(template_key)
            if not template:
                print(f"❌ Шаблон {template_key} не найден")
                return False
            
            print(f"📢 Отправка поста: {template['title']}")
            
            # Форматируем сообщение
            message_text = f"📢 <b>{template['title']}</b>\n\n{template['content']}"
            message_text += f"\n\n🛍 Перейти в каталог: /start"
            
            # Создаем кнопки
            keyboard = self.create_post_keyboard()
            
            # Отправляем в канал
            try:
                if template.get('image'):
                    result = self.bot.send_photo(self.channel_id, template['image'], message_text, keyboard)
                else:
                    result = self.bot.send_message(self.channel_id, message_text, keyboard)
                
                if result and result.get('ok'):
                    print(f"✅ Пост отправлен: {template['title']}")
                    
                    # Отправляем популярные товары после основного поста
                    time.sleep(3)
                    self.send_popular_products()
                    
                    # Записываем статистику
                    self.log_post_statistics(template_key, 1, 0)
                    return True
                else:
                    print(f"❌ Ошибка отправки поста: {result}")
                    self.log_post_statistics(template_key, 0, 1)
                    return False
                    
            except Exception as e:
                print(f"❌ Ошибка отправки поста: {e}")
                self.log_post_statistics(template_key, 0, 1)
                return False
                
        except Exception as e:
            print(f"❌ Ошибка обработки поста {template_key}: {e}")
            return False
    
    def send_custom_post(self, title, content, image_url=None):
        """Отправка кастомного поста"""
        try:
            message_text = f"📢 <b>{title}</b>\n\n{content}"
            message_text += f"\n\n🛍 Перейти в каталог: /start"
            
            keyboard = self.create_post_keyboard()
            
            if image_url:
                result = self.bot.send_photo(self.channel_id, image_url, message_text, keyboard)
            else:
                result = self.bot.send_message(self.channel_id, message_text, keyboard)
            
            if result and result.get('ok'):
                print(f"✅ Кастомный пост отправлен: {title}")
                
                # Отправляем товары после поста
                time.sleep(3)
                self.send_popular_products()
                
                self.log_post_statistics('custom', 1, 0)
                return True
            else:
                print(f"❌ Ошибка отправки кастомного поста: {result}")
                self.log_post_statistics('custom', 0, 1)
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отправки кастомного поста: {e}")
            return False
    
    def send_popular_products(self):
        """Отправка популярных товаров после основного поста"""
        try:
            # Получаем 3 самых популярных товара
            popular_products = self.db.execute_query('''
                SELECT id, name, price, image_url, views, sales_count
                FROM products
                WHERE is_active = 1 AND stock > 0
                ORDER BY (views * 0.3 + sales_count * 0.7) DESC
                LIMIT 3
            ''')
            
            if not popular_products:
                return
            
            for product in popular_products:
                self.send_product_card(product)
                time.sleep(2)  # Пауза между товарами
                
        except Exception as e:
            print(f"Ошибка отправки популярных товаров: {e}")
    
    def send_product_card(self, product):
        """Отправка карточки товара"""
        try:
            product_id, name, price, image_url, views, sales_count = product
            
            # Получаем отзывы
            reviews = self.db.execute_query('''
                SELECT AVG(rating) as avg_rating, COUNT(*) as reviews_count
                FROM reviews
                WHERE product_id = ?
            ''', (product_id,))
            
            avg_rating = reviews[0][0] if reviews and reviews[0][0] else 0
            reviews_count = reviews[0][1] if reviews else 0
            
            # Форматируем сообщение
            product_message = f"🛍 <b>{name}</b>\n\n"
            product_message += f"💰 Цена: <b>${price:.2f}</b>\n"
            
            if avg_rating > 0:
                stars = '⭐' * int(avg_rating)
                product_message += f"⭐ Рейтинг: {stars} {avg_rating:.1f}/5 ({reviews_count} отзывов)\n"
            
            product_message += f"👁 Просмотров: {views}\n"
            product_message += f"🛒 Продано: {sales_count} шт.\n\n"
            product_message += f"🔥 Популярный товар в нашем каталоге!"
            
            # Создаем кнопки для товара
            product_keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🛒 Заказать товар', 'url': f'https://t.me/your_bot_username?start=product_{product_id}'},
                        {'text': '⭐ Все отзывы', 'url': f'https://t.me/your_bot_username?start=reviews_{product_id}'}
                    ]
                ]
            }
            
            # Отправляем товар
            if image_url:
                self.bot.send_photo(self.channel_id, image_url, product_message, product_keyboard)
            else:
                self.bot.send_message(self.channel_id, product_message, product_keyboard)
                
        except Exception as e:
            print(f"Ошибка отправки карточки товара: {e}")
    
    def create_post_keyboard(self):
        """Создание клавиатуры для постов"""
        return {
            'inline_keyboard': [
                [
                    {'text': '🛒 Открыть каталог', 'url': 'https://t.me/your_bot_username?start=catalog'},
                    {'text': '🌐 Наш сайт', 'url': 'https://your-website.com'}
                ],
                [
                    {'text': '💬 Поддержка', 'url': 'https://t.me/your_support_username'},
                    {'text': '📱 Заказать в боте', 'url': 'https://t.me/your_bot_username'}
                ]
            ]
        }
    
    def send_birthday_post(self, customer_name=None):
        """Отправка поздравления с днем рождения"""
        birthday_content = f'''🎉 <b>С Днем Рождения!</b>

🎂 Сегодня особенный день{f" у {customer_name}" if customer_name else ""}!

🎁 <b>Праздничные подарки:</b>
• Скидка 20% на все товары
• Промокод: BIRTHDAY20
• Бесплатная доставка
• Подарочная упаковка

🥳 Пусть этот день будет наполнен радостью и приятными сюрпризами!

💝 Выберите себе подарок в нашем каталоге!'''
        
        return self.send_custom_post('С Днем Рождения! 🎂', birthday_content)
    
    def send_flash_sale_post(self, discount_percent=30, duration_hours=24):
        """Отправка поста о флеш-распродаже"""
        flash_content = f'''⚡ <b>ФЛЕШ-РАСПРОДАЖА!</b>

🔥 <b>ТОЛЬКО {duration_hours} ЧАСОВ:</b>
• Скидка {discount_percent}% на ВСЕ товары
• Промокод: FLASH{discount_percent}
• Количество ограничено!

⏰ <b>Торопитесь!</b>
До конца акции осталось мало времени!

💨 Самые быстрые получат лучшие товары!
🛒 Заказывайте прямо сейчас!'''
        
        return self.send_custom_post('Флеш-распродажа! ⚡', flash_content)
    
    def send_new_product_post(self, product_id):
        """Отправка поста о новом товаре"""
        try:
            product = self.db.get_product_by_id(product_id)
            if not product:
                return False
            
            new_product_content = f'''🆕 <b>НОВИНКА В КАТАЛОГЕ!</b>

✨ <b>{product[1]}</b>

📝 {product[2][:150] if product[2] else 'Отличный товар для наших покупателей!'}

💰 Цена: <b>${product[3]:.2f}</b>
📦 В наличии: {product[7]} шт.

🎁 <b>Для первых покупателей:</b>
• Скидка 10% на новинку
• Приоритетная доставка
• Гарантия лучшей цены

🚀 Будьте первыми, кто оценит новинку!'''
            
            message_text = f"📢 <b>Новинка в каталоге! ✨</b>\n\n{new_product_content}"
            message_text += f"\n\n🛍 Заказать: /start"
            
            # Специальная клавиатура для товара
            product_keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🛒 Заказать товар', 'url': f'https://t.me/your_bot_username?start=product_{product_id}'},
                        {'text': '📱 Открыть каталог', 'url': 'https://t.me/your_bot_username?start=catalog'}
                    ],
                    [
                        {'text': '🌐 Подробнее на сайте', 'url': f'https://your-website.com/product/{product_id}'},
                        {'text': '💬 Задать вопрос', 'url': 'https://t.me/your_support_username'}
                    ]
                ]
            }
            
            # Отправляем
            if product[6]:  # image_url
                result = self.bot.send_photo(self.channel_id, product[6], message_text, product_keyboard)
            else:
                result = self.bot.send_message(self.channel_id, message_text, product_keyboard)
            
            return result and result.get('ok')
            
        except Exception as e:
            print(f"Ошибка отправки поста о новом товаре: {e}")
            return False
    
    def log_post_statistics(self, post_type, sent_count, error_count):
        """Логирование статистики постов"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute_query('''
                INSERT INTO autopost_statistics (
                    post_type, sent_count, error_count, sent_at
                ) VALUES (?, ?, ?, ?)
            ''', (post_type, sent_count, error_count, current_time))
        except Exception as e:
            print(f"Ошибка записи статистики постов: {e}")
    
    def get_post_statistics(self, days=7):
        """Получение статистики постов"""
        try:
            return self.db.execute_query('''
                SELECT post_type, SUM(sent_count) as total_sent, SUM(error_count) as total_errors,
                       COUNT(*) as posts_count, MAX(sent_at) as last_sent
                FROM autopost_statistics
                WHERE sent_at >= date('now', '-{} days')
                GROUP BY post_type
                ORDER BY total_sent DESC
            '''.format(days))
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return []
    
    def get_available_templates(self):
        """Получение доступных шаблонов"""
        templates_info = []
        for key, template in self.post_templates.items():
            templates_info.append({
                'key': key,
                'title': template['title'],
                'description': template['content'][:100] + '...'
            })
        return templates_info
    
    def test_channel_connection(self):
        """Тест соединения с каналом"""
        test_message = f"🧪 <b>Тест канала</b>\n\n"
        test_message += f"✅ Если вы видите это сообщение, интеграция работает!\n\n"
        test_message += f"📅 Время: {datetime.now().strftime('%H:%M:%S')}\n"
        test_message += f"🤖 Отправлено из веб-панели администратора"
        
        try:
            result = self.bot.send_message(self.channel_id, test_message)
            return result and result.get('ok')
        except Exception as e:
            print(f"Ошибка тестирования канала: {e}")
            return False

# Для обратной совместимости
AutoPostsManager = ScheduledPostsManager