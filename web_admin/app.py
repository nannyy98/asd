@@ .. @@
 import os
 import sys
 import uuid
+import time
 from datetime import datetime, timedelta
 from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
 from werkzeug.utils import secure_filename
@@ .. @@
 # Добавляем путь к модулям бота
 sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

-from database import DatabaseManager
-from bot_integration import TelegramBotIntegration
+try:
+    from database import DatabaseManager
+    from bot_integration import TelegramBotIntegration
+except ImportError as e:
+    print(f"Ошибка импорта: {e}")
+    sys.exit(1)

 app = Flask(__name__)
 app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')

 # Инициализация
-db = DatabaseManager()
-telegram_bot = TelegramBotIntegration()
+try:
+    db = DatabaseManager()
+    telegram_bot = TelegramBotIntegration()
+except Exception as e:
+    print(f"Ошибка инициализации: {e}")
+    db = None
+    telegram_bot = None

 # Настройки загрузки файлов
@@ .. @@
 @app.route('/login', methods=['GET', 'POST'])
 def login():
     if request.method == 'POST':
         username = request.form['username']
+        password = request.form.get('password', '')
         admin_name = os.getenv('ADMIN_NAME', 'AdminUser')
+        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
         
-        if username == admin_name:
+        if username == admin_name and password == admin_password:
             session['logged_in'] = True
             session['username'] = username
             return redirect(url_for('dashboard'))
         else:
-            flash('Неверное имя пользователя')
+            flash('Неверное имя пользователя или пароль')
     
     return render_template('login.html')
@@ .. @@
 @app.route('/')
 @login_required
 def dashboard():
+    if not db:
+        flash('База данных недоступна')
+        return render_template('error.html', error='Database connection failed')
+    
     # Статистика за сегодня
     today = datetime.now().strftime('%Y-%m-%d')
-    today_stats = db.execute_query('''
+    try:
+        today_stats = db.execute_query('''
+            SELECT 
+                COUNT(*) as orders_today,
+                COALESCE(SUM(total_amount), 0) as revenue_today,
+                COUNT(DISTINCT user_id) as customers_today
+            FROM orders 
+            WHERE DATE(created_at) = ? AND status != 'cancelled'
+        ''', (today,))
+        
+        # Статистика за вчера
+        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
+        yesterday_stats = db.execute_query('''
+            SELECT 
+                COUNT(*) as orders_yesterday,
+                COALESCE(SUM(total_amount), 0) as revenue_yesterday
+            FROM orders 
+            WHERE DATE(created_at) = ? AND status != 'cancelled'
+        ''', (yesterday,))
+        
+        # Общая статистика
+        total_stats = db.execute_query('''
+            SELECT 
+                (SELECT COUNT(*) FROM users WHERE is_admin = 0) as total_customers,
+                COUNT(*) as total_orders,
+                COALESCE(SUM(total_amount), 0) as total_revenue
+            FROM orders
+            WHERE status != 'cancelled'
+        ''')
+        
+        # Последние заказы
+        recent_orders = db.execute_query('''
+            SELECT o.id, o.total_amount, o.status, o.created_at, u.name
+            FROM orders o
+            JOIN users u ON o.user_id = u.id
+            ORDER BY o.created_at DESC
+            LIMIT 10
+        ''')
+        
+        # Топ товары за неделю
+        top_products = db.execute_query('''
+            SELECT p.name, SUM(oi.quantity) as sold, SUM(oi.quantity * oi.price) as revenue
+            FROM order_items oi
+            JOIN products p ON oi.product_id = p.id
+            JOIN orders o ON oi.order_id = o.id
+            WHERE o.created_at >= date('now', '-7 days')
+            AND o.status != 'cancelled'
+            GROUP BY p.id, p.name
+            ORDER BY revenue DESC
+            LIMIT 5
+        ''')
+        
+    except Exception as e:
+        flash(f'Ошибка загрузки данных: {e}')
+        today_stats = [(0, 0, 0)]
+        yesterday_stats = [(0, 0)]
+        total_stats = [(0, 0, 0)]
+        recent_orders = []
+        top_products = []
+    
+    return render_template('dashboard.html',
+                         today_stats=today_stats[0] if today_stats else (0, 0, 0),
+                         yesterday_stats=yesterday_stats[0] if yesterday_stats else (0, 0),
+                         total_stats=total_stats[0] if total_stats else (0, 0, 0),
+                         recent_orders=recent_orders or [],
+                         top_products=top_products or [])

@app.route('/orders')
@login_required
def orders():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     page = int(request.args.get('page', 1))
     per_page = 20
     status_filter = request.args.get('status', '')
     search = request.args.get('search', '')
     
-    # Базовый запрос
-    query = '''
-        SELECT o.id, o.total_amount, o.status, o.created_at, u.name, u.phone, u.email, 
-               o.delivery_address, o.payment_method
-        FROM orders o
-        JOIN users u ON o.user_id = u.id
-        WHERE 1=1
-    '''
-    params = []
-    
-    # Фильтры
-    if status_filter:
-        query += ' AND o.status = ?'
-        params.append(status_filter)
-    
-    if search:
-        query += ' AND (u.name LIKE ? OR o.id = ?)'
-        params.extend([f'%{search}%', search])
-    
-    query += ' ORDER BY o.created_at DESC'
-    
-    # Получаем все заказы для подсчета страниц
-    all_orders = db.execute_query(query, params)
-    total_orders = len(all_orders) if all_orders else 0
-    total_pages = (total_orders + per_page - 1) // per_page
-    
-    # Получаем заказы для текущей страницы
-    offset = (page - 1) * per_page
-    paginated_query = query + f' LIMIT {per_page} OFFSET {offset}'
-    orders_data = db.execute_query(paginated_query, params)
+    try:
+        # Базовый запрос
+        query = '''
+            SELECT o.id, o.total_amount, o.status, o.created_at, u.name, u.phone, u.email, 
+                   o.delivery_address, o.payment_method
+            FROM orders o
+            JOIN users u ON o.user_id = u.id
+            WHERE 1=1
+        '''
+        params = []
+        
+        # Фильтры
+        if status_filter:
+            query += ' AND o.status = ?'
+            params.append(status_filter)
+        
+        if search:
+            if search.isdigit():
+                query += ' AND o.id = ?'
+                params.append(int(search))
+            else:
+                query += ' AND u.name LIKE ?'
+                params.append(f'%{search}%')
+        
+        query += ' ORDER BY o.created_at DESC'
+        
+        # Получаем все заказы для подсчета страниц
+        all_orders = db.execute_query(query, params)
+        total_orders = len(all_orders) if all_orders else 0
+        total_pages = (total_orders + per_page - 1) // per_page
+        
+        # Получаем заказы для текущей страницы
+        offset = (page - 1) * per_page
+        paginated_query = query + f' LIMIT {per_page} OFFSET {offset}'
+        orders_data = db.execute_query(paginated_query, params)
+        
+    except Exception as e:
+        flash(f'Ошибка загрузки заказов: {e}')
+        orders_data = []
+        total_pages = 1
     
     return render_template('orders.html',
                          orders=orders_data or [],
@@ .. @@
 @app.route('/products')
 @login_required
 def products():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     page = int(request.args.get('page', 1))
     per_page = 20
     category_filter = request.args.get('category', '')
     search = request.args.get('search', '')
     
-    # Получаем категории для фильтра
-    categories = db.get_categories()
-    
-    # Базовый запрос
-    query = '''
-        SELECT p.id, p.name, p.price, p.stock, p.is_active, c.name as category_name,
-               p.sales_count, p.views
-        FROM products p
-        JOIN categories c ON p.category_id = c.id
-        WHERE 1=1
-    '''
-    params = []
-    
-    # Фильтры
-    if category_filter:
-        query += ' AND p.category_id = ?'
-        params.append(category_filter)
-    
-    if search:
-        query += ' AND p.name LIKE ?'
-        params.append(f'%{search}%')
-    
-    query += ' ORDER BY p.created_at DESC'
-    
-    # Получаем все товары для подсчета страниц
-    all_products = db.execute_query(query, params)
-    total_products = len(all_products) if all_products else 0
-    total_pages = (total_products + per_page - 1) // per_page
-    
-    # Получаем товары для текущей страницы
-    offset = (page - 1) * per_page
-    paginated_query = query + f' LIMIT {per_page} OFFSET {offset}'
-    products_data = db.execute_query(paginated_query, params)
+    try:
+        # Получаем категории для фильтра
+        categories = db.get_categories()
+        
+        # Базовый запрос
+        query = '''
+            SELECT p.id, p.name, p.price, p.stock, p.is_active, c.name as category_name,
+                   p.sales_count, p.views
+            FROM products p
+            LEFT JOIN categories c ON p.category_id = c.id
+            WHERE 1=1
+        '''
+        params = []
+        
+        # Фильтры
+        if category_filter:
+            query += ' AND p.category_id = ?'
+            params.append(int(category_filter))
+        
+        if search:
+            query += ' AND p.name LIKE ?'
+            params.append(f'%{search}%')
+        
+        query += ' ORDER BY p.created_at DESC'
+        
+        # Получаем все товары для подсчета страниц
+        all_products = db.execute_query(query, params)
+        total_products = len(all_products) if all_products else 0
+        total_pages = (total_products + per_page - 1) // per_page
+        
+        # Получаем товары для текущей страницы
+        offset = (page - 1) * per_page
+        paginated_query = query + f' LIMIT {per_page} OFFSET {offset}'
+        products_data = db.execute_query(paginated_query, params)
+        
+    except Exception as e:
+        flash(f'Ошибка загрузки товаров: {e}')
+        categories = []
+        products_data = []
+        total_pages = 1
     
     return render_template('products.html',
                          products=products_data or [],
@@ .. @@
 @app.route('/add_product', methods=['GET', 'POST'])
 @login_required
 def add_product():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     if request.method == 'POST':
-        name = request.form['name']
-        description = request.form.get('description', '')
-        price = float(request.form['price'])
-        cost_price = float(request.form.get('cost_price', 0))
-        category_id = int(request.form['category_id'])
-        stock = int(request.form['stock'])
-        
-        # Обработка изображения
-        image_url = ''
-        if 'image_file' in request.files and request.files['image_file'].filename:
-            file = request.files['image_file']
-            if file and allowed_file(file.filename):
-                filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
-                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
-                file.save(file_path)
-                image_url = f'/static/uploads/{filename}'
-        elif request.form.get('image_url'):
-            image_url = request.form['image_url']
-        
-        # Добавляем товар
-        product_id = db.execute_query('''
-            INSERT INTO products (name, description, price, cost_price, category_id, image_url, stock)
-            VALUES (?, ?, ?, ?, ?, ?, ?)
-        ''', (name, description, price, cost_price, category_id, image_url, stock))
-        
-        if product_id:
-            # Уведомляем админов в Telegram
-            admin_message = f"✅ <b>Новый товар добавлен!</b>\n\n"
-            admin_message += f"🛍 <b>{name}</b>\n"
-            admin_message += f"💰 Цена: ${price:.2f}\n"
-            admin_message += f"📦 Остаток: {stock} шт.\n"
-            admin_message += f"📅 Добавлен через веб-панель"
-            
-            telegram_bot.notify_admins(admin_message)
-            
-            # Сигнализируем боту о необходимости обновления
-            telegram_bot.trigger_bot_data_reload()
-            
-            flash(f'Товар "{name}" успешно добавлен!')
-            return redirect(url_for('products'))
-        else:
-            flash('Ошибка добавления товара')
+        try:
+            name = request.form['name']
+            description = request.form.get('description', '')
+            price = float(request.form['price'])
+            cost_price = float(request.form.get('cost_price', 0))
+            category_id = int(request.form['category_id'])
+            stock = int(request.form['stock'])
+            
+            # Обработка изображения
+            image_url = ''
+            if 'image_file' in request.files and request.files['image_file'].filename:
+                file = request.files['image_file']
+                if file and allowed_file(file.filename):
+                    filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
+                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
+                    file.save(file_path)
+                    image_url = f'/static/uploads/{filename}'
+            elif request.form.get('image_url'):
+                image_url = request.form['image_url']
+            
+            # Добавляем товар
+            product_id = db.execute_query('''
+                INSERT INTO products (name, description, price, cost_price, category_id, image_url, stock, is_active)
+                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
+            ''', (name, description, price, cost_price, category_id, image_url, stock))
+            
+            if product_id:
+                # Уведомляем админов в Telegram
+                if telegram_bot:
+                    admin_message = f"✅ <b>Новый товар добавлен!</b>\n\n"
+                    admin_message += f"🛍 <b>{name}</b>\n"
+                    admin_message += f"💰 Цена: ${price:.2f}\n"
+                    admin_message += f"📦 Остаток: {stock} шт.\n"
+                    admin_message += f"📅 Добавлен через веб-панель"
+                    
+                    telegram_bot.notify_admins(admin_message)
+                    telegram_bot.trigger_bot_data_reload()
+                
+                flash(f'Товар "{name}" успешно добавлен!')
+                return redirect(url_for('products'))
+            else:
+                flash('Ошибка добавления товара')
+        except ValueError as e:
+            flash(f'Ошибка в данных: {e}')
+        except Exception as e:
+            flash(f'Ошибка добавления товара: {e}')
     
-    categories = db.get_categories()
+    try:
+        categories = db.get_categories()
+    except Exception as e:
+        flash(f'Ошибка загрузки категорий: {e}')
+        categories = []
+    
     return render_template('add_product.html', categories=categories or [])
@@ .. @@
 @app.route('/categories')
 @login_required
 def categories():
-    categories_data = db.execute_query('''
-        SELECT c.id, c.name, c.description, c.emoji, c.is_active,
-               COUNT(p.id) as products_count
-        FROM categories c
-        LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1
-        GROUP BY c.id, c.name, c.description, c.emoji, c.is_active
-        ORDER BY c.name
-    ''')
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
+    try:
+        categories_data = db.execute_query('''
+            SELECT c.id, c.name, c.description, c.emoji, c.is_active,
+                   COUNT(p.id) as products_count
+            FROM categories c
+            LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1
+            GROUP BY c.id, c.name, c.description, c.emoji, c.is_active
+            ORDER BY c.name
+        ''')
+    except Exception as e:
+        flash(f'Ошибка загрузки категорий: {e}')
+        categories_data = []
     
     return render_template('categories.html', categories=categories_data or [])
@@ .. @@
 @app.route('/add_category', methods=['GET', 'POST'])
 @login_required
 def add_category():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     if request.method == 'POST':
-        name = request.form['name']
-        description = request.form.get('description', '')
-        emoji = request.form.get('emoji', '')
-        
-        category_id = db.execute_query('''
-            INSERT INTO categories (name, description, emoji)
-            VALUES (?, ?, ?)
-        ''', (name, description, emoji))
-        
-        if category_id:
-            # Уведомляем админов в Telegram
-            admin_message = f"✅ <b>Новая категория добавлена!</b>\n\n"
-            admin_message += f"📂 <b>{emoji} {name}</b>\n"
-            admin_message += f"📝 {description}\n"
-            admin_message += f"📅 Добавлена через веб-панель"
-            
-            telegram_bot.notify_admins(admin_message)
-            
-            # Сигнализируем боту о необходимости обновления
-            telegram_bot.trigger_bot_data_reload()
-            
-            flash(f'Категория "{name}" успешно добавлена!')
-            return redirect(url_for('categories'))
-        else:
-            flash('Ошибка добавления категории')
+        try:
+            name = request.form['name']
+            description = request.form.get('description', '')
+            emoji = request.form.get('emoji', '')
+            
+            category_id = db.execute_query('''
+                INSERT INTO categories (name, description, emoji, is_active)
+                VALUES (?, ?, ?, 1)
+            ''', (name, description, emoji))
+            
+            if category_id:
+                # Уведомляем админов в Telegram
+                if telegram_bot:
+                    admin_message = f"✅ <b>Новая категория добавлена!</b>\n\n"
+                    admin_message += f"📂 <b>{emoji} {name}</b>\n"
+                    admin_message += f"📝 {description}\n"
+                    admin_message += f"📅 Добавлена через веб-панель"
+                    
+                    telegram_bot.notify_admins(admin_message)
+                    telegram_bot.trigger_bot_data_reload()
+                
+                flash(f'Категория "{name}" успешно добавлена!')
+                return redirect(url_for('categories'))
+            else:
+                flash('Ошибка добавления категории')
+        except Exception as e:
+            flash(f'Ошибка добавления категории: {e}')
     
     return render_template('add_category.html')
@@ .. @@
 @app.route('/customers')
 @login_required
 def customers():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     page = int(request.args.get('page', 1))
     per_page = 20
     search = request.args.get('search', '')
     
-    # Базовый запрос
-    query = '''
-        SELECT u.id, u.name, u.phone, u.email, u.created_at,
-               COUNT(o.id) as orders_count,
-               COALESCE(SUM(o.total_amount), 0) as total_spent,
-               MAX(o.created_at) as last_order
-        FROM users u
-        LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
-        WHERE u.is_admin = 0
-    '''
-    params = []
-    
-    if search:
-        query += ' AND (u.name LIKE ? OR u.phone LIKE ? OR u.email LIKE ?)'
-        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
-    
-    query += ' GROUP BY u.id ORDER BY total_spent DESC'
-    
-    # Получаем всех клиентов для подсчета страниц
-    all_customers = db.execute_query(query, params)
-    total_customers = len(all_customers) if all_customers else 0
-    total_pages = (total_customers + per_page - 1) // per_page
-    
-    # Получаем клиентов для текущей страницы
-    offset = (page - 1) * per_page
-    paginated_query = query + f' LIMIT {per_page} OFFSET {offset}'
-    customers_data = db.execute_query(paginated_query, params)
+    try:
+        # Базовый запрос
+        query = '''
+            SELECT u.id, u.name, u.phone, u.email, u.created_at,
+                   COUNT(o.id) as orders_count,
+                   COALESCE(SUM(o.total_amount), 0) as total_spent,
+                   MAX(o.created_at) as last_order
+            FROM users u
+            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
+            WHERE u.is_admin = 0
+        '''
+        params = []
+        
+        if search:
+            query += ' AND (u.name LIKE ? OR COALESCE(u.phone, "") LIKE ? OR COALESCE(u.email, "") LIKE ?)'
+            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
+        
+        query += ' GROUP BY u.id ORDER BY total_spent DESC'
+        
+        # Получаем всех клиентов для подсчета страниц
+        all_customers = db.execute_query(query, params)
+        total_customers = len(all_customers) if all_customers else 0
+        total_pages = (total_customers + per_page - 1) // per_page
+        
+        # Получаем клиентов для текущей страницы
+        offset = (page - 1) * per_page
+        paginated_query = query + f' LIMIT {per_page} OFFSET {offset}'
+        customers_data = db.execute_query(paginated_query, params)
+        
+    except Exception as e:
+        flash(f'Ошибка загрузки клиентов: {e}')
+        customers_data = []
+        total_pages = 1
     
     return render_template('customers.html',
                          customers=customers_data or [],
@@ .. @@
 @app.route('/analytics')
 @login_required
 def analytics_page():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     period = request.args.get('period', '30')
     
     try:
-        from analytics import AnalyticsManager
-        analytics = AnalyticsManager(db)
-        
         end_date = datetime.now().strftime('%Y-%m-%d')
         start_date = (datetime.now() - timedelta(days=int(period))).strftime('%Y-%m-%d')
         
-        sales_report = analytics.get_sales_report(start_date, end_date)
+        # Простая аналитика без внешних модулей
+        sales_data = db.execute_query('''
+            SELECT 
+                COUNT(*) as orders_count,
+                SUM(total_amount) as revenue,
+                AVG(total_amount) as avg_order_value,
+                COUNT(DISTINCT user_id) as unique_customers
+            FROM orders 
+            WHERE DATE(created_at) BETWEEN ? AND ?
+            AND status != 'cancelled'
+        ''', (start_date, end_date))
+        
+        top_products = db.execute_query('''
+            SELECT 
+                p.name,
+                SUM(oi.quantity) as units_sold,
+                SUM(oi.quantity * oi.price) as revenue
+            FROM order_items oi
+            JOIN products p ON oi.product_id = p.id
+            JOIN orders o ON oi.order_id = o.id
+            WHERE DATE(o.created_at) BETWEEN ? AND ?
+            AND o.status != 'cancelled'
+            GROUP BY p.id, p.name
+            ORDER BY revenue DESC
+            LIMIT 10
+        ''', (start_date, end_date))
+        
+        sales_report = {
+            'period': f"{start_date} - {end_date}",
+            'sales_data': sales_data,
+            'top_products': top_products
+        }
         
         return render_template('analytics.html',
                              sales_report=sales_report,
                              period=period)
-    except ImportError:
-        flash('Модуль аналитики недоступен')
+    except Exception as e:
+        flash(f'Ошибка загрузки аналитики: {e}')
         return redirect(url_for('dashboard'))
@@ .. @@
 @app.route('/financial')
 @login_required
 def financial():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     period = request.args.get('period', '30')
     
     try:
-        from financial_reports import FinancialReportsManager
-        financial_manager = FinancialReportsManager(db)
-        
         end_date = datetime.now().strftime('%Y-%m-%d')
         start_date = (datetime.now() - timedelta(days=int(period))).strftime('%Y-%m-%d')
         
-        profit_loss = financial_manager.generate_profit_loss_report(start_date, end_date)
-        cash_flow = financial_manager.generate_cash_flow_report(start_date, end_date)
+        # Простые финансовые отчеты
+        revenue_data = db.execute_query('''
+            SELECT 
+                SUM(total_amount) as gross_revenue,
+                SUM(promo_discount) as total_discounts,
+                COUNT(*) as orders_count
+            FROM orders 
+            WHERE DATE(created_at) BETWEEN ? AND ?
+            AND status != 'cancelled'
+        ''', (start_date, end_date))
+        
+        profit_loss = {
+            'period': f"{start_date} - {end_date}",
+            'gross_revenue': revenue_data[0][0] or 0,
+            'discounts': revenue_data[0][1] or 0,
+            'net_revenue': (revenue_data[0][0] or 0) - (revenue_data[0][1] or 0),
+            'orders_count': revenue_data[0][2] or 0
+        }
+        
+        cash_flow = {
+            'period': f"{start_date} - {end_date}",
+            'total_inflow': revenue_data[0][0] or 0,
+            'total_outflow': 0,
+            'net_cash_flow': revenue_data[0][0] or 0,
+            'daily_data': []
+        }
         
         return render_template('financial.html',
                              profit_loss=profit_loss,
                              cash_flow=cash_flow,
                              period=period)
-    except ImportError:
-        flash('Модуль финансовых отчетов недоступен')
+    except Exception as e:
+        flash(f'Ошибка загрузки финансовых данных: {e}')
         return redirect(url_for('dashboard'))
@@ .. @@
 @app.route('/inventory')
 @login_required
 def inventory_page():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     try:
-        from inventory_management import InventoryManager
-        inventory_manager = InventoryManager(db)
-        
-        inventory_summary = inventory_manager.get_inventory_summary()
-        low_stock = inventory_manager.check_stock_levels()
-        abc_analysis = inventory_manager.get_abc_inventory_analysis()
+        # Простая сводка по складу
+        inventory_summary = db.execute_query('''
+            SELECT 
+                COUNT(*) as total_products,
+                SUM(stock) as total_units,
+                SUM(stock * price) as total_value,
+                COUNT(CASE WHEN stock = 0 THEN 1 END) as out_of_stock,
+                COUNT(CASE WHEN stock <= 5 THEN 1 END) as low_stock
+            FROM products
+            WHERE is_active = 1
+        ''')[0]
+        
+        inventory_data = {
+            'total_products': inventory_summary[0],
+            'total_units': inventory_summary[1],
+            'total_value': inventory_summary[2],
+            'out_of_stock': inventory_summary[3],
+            'low_stock': inventory_summary[4],
+            'top_value_products': []
+        }
+        
+        low_stock_data = {
+            'critical': db.execute_query('SELECT id, name, stock FROM products WHERE stock = 0 AND is_active = 1'),
+            'low': db.execute_query('SELECT id, name, stock FROM products WHERE stock > 0 AND stock <= 5 AND is_active = 1'),
+            'total_affected': inventory_summary[4]
+        }
+        
+        abc_analysis = {'categories': {}, 'total_value': inventory_summary[2]}
         
         return render_template('inventory.html',
-                             inventory_summary=inventory_summary,
-                             low_stock=low_stock,
+                             inventory_summary=inventory_data,
+                             low_stock=low_stock_data,
                              abc_analysis=abc_analysis)
-    except ImportError:
-        flash('Модуль управления складом недоступен')
+    except Exception as e:
+        flash(f'Ошибка загрузки данных склада: {e}')
         return redirect(url_for('dashboard'))
@@ .. @@
 @app.route('/crm')
 @login_required
 def crm_page():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     try:
-        from crm import CRMManager
-        crm_manager = CRMManager(db)
-        
-        segments = crm_manager.segment_customers()
-        at_risk_customers = crm_manager.get_churn_risk_customers()
+        # Простая сегментация клиентов
+        segments = {
+            'champions': [],
+            'loyal': [],
+            'new': [],
+            'at_risk': []
+        }
+        
+        # Получаем клиентов с базовой сегментацией
+        customers = db.execute_query('''
+            SELECT 
+                u.id, u.name, u.created_at,
+                COUNT(o.id) as orders_count,
+                COALESCE(SUM(o.total_amount), 0) as total_spent
+            FROM users u
+            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
+            WHERE u.is_admin = 0
+            GROUP BY u.id, u.name, u.created_at
+        ''')
+        
+        for customer in customers or []:
+            if customer[4] >= 500:  # Потратили больше $500
+                segments['champions'].append(customer)
+            elif customer[3] >= 3:  # 3+ заказов
+                segments['loyal'].append(customer)
+            elif customer[3] == 0:  # Новые без заказов
+                segments['new'].append(customer)
+            else:
+                segments['at_risk'].append(customer)
+        
+        at_risk_customers = segments['at_risk']
         
         return render_template('crm.html',
                              segments=segments,
                              at_risk_customers=at_risk_customers)
-    except ImportError:
-        flash('Модуль CRM недоступен')
+    except Exception as e:
+        flash(f'Ошибка загрузки CRM данных: {e}')
         return redirect(url_for('dashboard'))
@@ .. @@
 @app.route('/scheduled_posts')
 @login_required
 def scheduled_posts():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     try:
         posts = db.execute_query('''
             SELECT id, title, content, time_morning, time_afternoon, time_evening,
@@ .. @@
 @app.route('/create_post', methods=['GET', 'POST'])
 @login_required
 def create_post():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('dashboard'))
+    
     if request.method == 'POST':
-        title = request.form['title']
-        content = request.form['content']
-        
-        # Обработка времени отправки
-        morning_time = request.form.get('morning_time') if request.form.get('morning_enabled') else None
-        afternoon_time = request.form.get('afternoon_time') if request.form.get('afternoon_enabled') else None
-        evening_time = request.form.get('evening_time') if request.form.get('evening_enabled') else None
-        
-        target_audience = request.form['target_audience']
-        
-        # Обработка изображения
-        image_url = ''
-        if 'image_file' in request.files and request.files['image_file'].filename:
-            file = request.files['image_file']
-            if file and allowed_file(file.filename):
-                filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
-                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
-                file.save(file_path)
-                image_url = f'/static/uploads/{filename}'
-        elif request.form.get('image_url'):
-            image_url = request.form['image_url']
-        
-        post_id = db.execute_query('''
-            INSERT INTO scheduled_posts (
-                title, content, time_morning, time_afternoon, time_evening,
-                target_audience, image_url, is_active, created_at
-            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
-        ''', (
-            title, content, morning_time, afternoon_time, evening_time,
-            target_audience, image_url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
-        ))
-        
-        if post_id:
-            # Сигнализируем боту о необходимости обновления
-            telegram_bot.trigger_bot_data_reload()
-            
-            flash(f'Автоматический пост "{title}" создан!')
-            return redirect(url_for('scheduled_posts'))
-        else:
-            flash('Ошибка создания поста')
+        try:
+            title = request.form['title']
+            content = request.form['content']
+            
+            # Обработка времени отправки
+            morning_time = request.form.get('morning_time') if request.form.get('morning_enabled') else None
+            afternoon_time = request.form.get('afternoon_time') if request.form.get('afternoon_enabled') else None
+            evening_time = request.form.get('evening_time') if request.form.get('evening_enabled') else None
+            
+            target_audience = request.form['target_audience']
+            
+            # Обработка изображения
+            image_url = ''
+            if 'image_file' in request.files and request.files['image_file'].filename:
+                file = request.files['image_file']
+                if file and allowed_file(file.filename):
+                    filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
+                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
+                    file.save(file_path)
+                    image_url = f'/static/uploads/{filename}'
+            elif request.form.get('image_url'):
+                image_url = request.form['image_url']
+            
+            post_id = db.execute_query('''
+                INSERT INTO scheduled_posts (
+                    title, content, time_morning, time_afternoon, time_evening,
+                    target_audience, image_url, is_active, created_at
+                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
+            ''', (
+                title, content, morning_time, afternoon_time, evening_time,
+                target_audience, image_url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
+            ))
+            
+            if post_id:
+                # Сигнализируем боту о необходимости обновления
+                if telegram_bot:
+                    telegram_bot.trigger_bot_data_reload()
+                
+                flash(f'Автоматический пост "{title}" создан!')
+                return redirect(url_for('scheduled_posts'))
+            else:
+                flash('Ошибка создания поста')
+        except Exception as e:
+            flash(f'Ошибка создания поста: {e}')
     
     return render_template('create_post.html')
@@ .. @@
 @app.route('/update_order_status', methods=['POST'])
 @login_required
 def update_order_status():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('orders'))
+    
     order_id = request.form['order_id']
     status = request.form['status']
     
-    result = db.update_order_status(order_id, status)
-    
-    if result is not None:
-        # Уведомляем клиента об изменении статуса
-        try:
-            order_details = db.get_order_details(order_id)
-            if order_details:
-                user_id = order_details['order'][1]
-                user = db.execute_query('SELECT telegram_id, name FROM users WHERE id = ?', (user_id,))
-                
-                if user:
-                    status_messages = {
-                        'confirmed': 'подтвержден',
-                        'shipped': 'отправлен',
-                        'delivered': 'доставлен',
-                        'cancelled': 'отменен'
-                    }
-                    
-                    status_text = status_messages.get(status, status)
-                    notification = f"📦 <b>Обновление заказа #{order_id}</b>\n\n"
-                    notification += f"Статус изменен на: <b>{status_text}</b>\n\n"
-                    notification += f"Спасибо за покупку!"
-                    
-                    telegram_bot.send_message(user[0][0], notification)
-        except Exception as e:
-            print(f"Ошибка уведомления клиента: {e}")
-        
-        flash(f'Статус заказа #{order_id} изменен на "{status}"')
-    else:
-        flash('Ошибка обновления статуса заказа')
+    try:
+        result = db.update_order_status(order_id, status)
+        
+        if result is not None:
+            # Уведомляем клиента об изменении статуса
+            try:
+                order_details = db.get_order_details(order_id)
+                if order_details and telegram_bot:
+                    user_id = order_details['order'][1]
+                    user = db.execute_query('SELECT telegram_id, name FROM users WHERE id = ?', (user_id,))
+                    
+                    if user:
+                        status_messages = {
+                            'confirmed': 'подтвержден',
+                            'shipped': 'отправлен',
+                            'delivered': 'доставлен',
+                            'cancelled': 'отменен'
+                        }
+                        
+                        status_text = status_messages.get(status, status)
+                        notification = f"📦 <b>Обновление заказа #{order_id}</b>\n\n"
+                        notification += f"Статус изменен на: <b>{status_text}</b>\n\n"
+                        notification += f"Спасибо за покупку!"
+                        
+                        telegram_bot.send_message(user[0][0], notification)
+            except Exception as e:
+                print(f"Ошибка уведомления клиента: {e}")
+            
+            flash(f'Статус заказа #{order_id} изменен на "{status}"')
+        else:
+            flash('Ошибка обновления статуса заказа')
+    except Exception as e:
+        flash(f'Ошибка обновления статуса: {e}')
     
     return redirect(url_for('orders'))
@@ .. @@
 @app.route('/order_detail/<int:order_id>')
 @login_required
 def order_detail(order_id):
-    order_data = db.get_order_details(order_id)
-    
-    if not order_data:
-        flash('Заказ не найден')
+    if not db:
+        flash('База данных недоступна')
         return redirect(url_for('orders'))
     
-    return render_template('order_detail.html', order_data=order_data, db=db)
+    try:
+        order_data = db.get_order_details(order_id)
+        
+        if not order_data:
+            flash('Заказ не найден')
+            return redirect(url_for('orders'))
+        
+        return render_template('order_detail.html', order_data=order_data, db=db)
+    except Exception as e:
+        flash(f'Ошибка загрузки заказа: {e}')
+        return redirect(url_for('orders'))
@@ .. @@
 @app.route('/send_now_post', methods=['POST'])
 @login_required
 def send_now_post():
+    if not db or not telegram_bot:
+        flash('Сервисы недоступны')
+        return redirect(url_for('scheduled_posts'))
+    
     post_id = request.form['post_id']
     
-    # Получаем данные поста
-    post_data = db.execute_query(
-        'SELECT title, content, target_audience, image_url FROM scheduled_posts WHERE id = ?',
-        (post_id,)
-    )
-    
-    if not post_data:
-        flash('Пост не найден')
-        return redirect(url_for('scheduled_posts'))
-    
-    title, content, target_audience, image_url = post_data[0]
-    
-    # Отправляем немедленно
     try:
-        from scheduled_posts import ScheduledPostsManager
-        posts_manager = ScheduledPostsManager(None, db)
-        posts_manager.bot = telegram_bot
+        # Получаем данные поста
+        post_data = db.execute_query(
+            'SELECT title, content, target_audience, image_url FROM scheduled_posts WHERE id = ?',
+            (post_id,)
+        )
         
-        # Получаем получателей
-        recipients = posts_manager.get_target_audience(target_audience)
+        if not post_data:
+            flash('Пост не найден')
+            return redirect(url_for('scheduled_posts'))
         
-        if recipients:
-            message_text = posts_manager.format_post_message(title, content, 'manual')
-            keyboard = posts_manager.create_post_keyboard()
+        title, content, target_audience, image_url = post_data[0]
+        
+        # Получаем получателей
+        if target_audience == 'channel':
+            recipients = [('-1002566537425', 'Канал', 'ru')]
+        elif target_audience == 'all':
+            recipients = db.execute_query(
+                'SELECT telegram_id, name, language FROM users WHERE is_admin = 0'
+            )
+        elif target_audience == 'active':
+            recipients = db.execute_query('''
+                SELECT DISTINCT u.telegram_id, u.name, u.language
+                FROM users u
+                JOIN orders o ON u.id = o.user_id
+                WHERE u.is_admin = 0 AND o.created_at >= datetime('now', '-30 days')
+            ''')
+        else:
+            recipients = []
+        
+        if recipients:
+            # Форматируем сообщение
+            message_text = f"📢 <b>{title}</b>\n\n{content}\n\n🛍 Перейти в каталог: /start"
+            
+            # Создаем клавиатуру
+            keyboard = {
+                'inline_keyboard': [
+                    [
+                        {'text': '🛒 Заказать товары', 'url': 'https://t.me/your_bot_username'},
+                        {'text': '🌐 Перейти на сайт', 'url': 'https://your-website.com'}
+                    ]
+                ]
+            }
             
             success_count = 0
             error_count = 0
             
             for recipient in recipients:
                 try:
-                    if target_audience == 'channel':
-                        if image_url:
-                            result = telegram_bot.send_photo(posts_manager.channel_id, image_url, message_text, keyboard)
-                        else:
-                            result = telegram_bot.send_message(posts_manager.channel_id, message_text, keyboard)
+                    telegram_id = recipient[0]
+                    
+                    if image_url:
+                        result = telegram_bot.send_photo(telegram_id, image_url, message_text, keyboard)
                     else:
-                        telegram_id = recipient[0] if isinstance(recipient, (list, tuple)) else recipient.get('telegram_id')
-                        if image_url:
-                            result = telegram_bot.send_photo(telegram_id, image_url, message_text, keyboard)
-                        else:
-                            result = telegram_bot.send_message(telegram_id, message_text, keyboard)
+                        result = telegram_bot.send_message(telegram_id, message_text, keyboard)
                     
                     if result and result.get('ok'):
                         success_count += 1
                     else:
                         error_count += 1
+                        
+                    # Пауза между отправками
+                    time.sleep(0.1)
+                    
                 except Exception as e:
                     error_count += 1
                     print(f"Ошибка отправки: {e}")
             
-            # Если это канал, отправляем товары с отзывами
-            if target_audience == 'channel':
-                posts_manager.send_product_reviews_to_channel()
-            
             flash(f'Пост отправлен! Успешно: {success_count}, Ошибок: {error_count}')
         else:
             flash('Нет получателей для отправки')
@@ .. @@
 @app.route('/test_channel_post', methods=['POST'])
 @login_required
 def test_channel_post():
+    if not telegram_bot:
+        flash('Telegram бот недоступен')
+        return redirect(url_for('scheduled_posts'))
+    
     title = "🧪 Тест канала"
     content = "Это тестовое сообщение из веб-панели администратора.\n\n✅ Если вы видите это сообщение, интеграция работает корректно!\n\n📅 Время отправки: " + datetime.now().strftime('%H:%M:%S')
     test_image = "https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg"
@@ .. @@
 @app.route('/toggle_post_status', methods=['POST'])
 @login_required
 def toggle_post_status():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('scheduled_posts'))
+    
     post_id = request.form['post_id']
     current_status = int(request.form['current_status'])
     new_status = 0 if current_status else 1
     
-    result = db.execute_query(
-        'UPDATE scheduled_posts SET is_active = ? WHERE id = ?',
-        (new_status, post_id)
-    )
-    
-    if result is not None:
-        # Сигнализируем боту о необходимости обновления
-        telegram_bot.trigger_bot_data_reload()
-        
-        status_text = "включен" if new_status else "выключен"
-        flash(f'Пост {status_text}!')
-    else:
-        flash('Ошибка изменения статуса поста')
+    try:
+        result = db.execute_query(
+            'UPDATE scheduled_posts SET is_active = ?, updated_at = ? WHERE id = ?',
+            (new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), post_id)
+        )
+        
+        if result is not None:
+            # Сигнализируем боту о необходимости обновления
+            if telegram_bot:
+                telegram_bot.trigger_bot_data_reload()
+            
+            status_text = "включен" if new_status else "выключен"
+            flash(f'Пост {status_text}!')
+        else:
+            flash('Ошибка изменения статуса поста')
+    except Exception as e:
+        flash(f'Ошибка изменения статуса: {e}')
     
     return redirect(url_for('scheduled_posts'))
@@ .. @@
 @app.route('/api/chart_data')
 @login_required
 def chart_data():
+    if not db:
+        return jsonify({'labels': [], 'data': []})
+    
     chart_type = request.args.get('type', 'sales')
     period = int(request.args.get('period', 30))
     
     end_date = datetime.now()
     start_date = end_date - timedelta(days=period)
     
-    if chart_type == 'sales':
-        # Данные продаж по дням
-        sales_data = db.execute_query('''
-            SELECT 
-                DATE(created_at) as date,
-                COALESCE(SUM(total_amount), 0) as daily_revenue
-            FROM orders
-            WHERE DATE(created_at) BETWEEN ? AND ?
-            AND status != 'cancelled'
-            GROUP BY DATE(created_at)
-            ORDER BY date
-        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
-        
-        labels = [item[0] for item in sales_data] if sales_data else []
-        data = [float(item[1]) for item in sales_data] if sales_data else []
-        
-    elif chart_type == 'orders':
-        # Количество заказов по дням
-        orders_data = db.execute_query('''
-            SELECT 
-                DATE(created_at) as date,
-                COUNT(*) as daily_orders
-            FROM orders
-            WHERE DATE(created_at) BETWEEN ? AND ?
-            AND status != 'cancelled'
-            GROUP BY DATE(created_at)
-            ORDER BY date
-        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
-        
-        labels = [item[0] for item in orders_data] if orders_data else []
-        data = [item[1] for item in orders_data] if orders_data else []
-    
-    else:
-        labels = []
-        data = []
+    try:
+        if chart_type == 'sales':
+            # Данные продаж по дням
+            sales_data = db.execute_query('''
+                SELECT 
+                    DATE(created_at) as date,
+                    COALESCE(SUM(total_amount), 0) as daily_revenue
+                FROM orders
+                WHERE DATE(created_at) BETWEEN ? AND ?
+                AND status != 'cancelled'
+                GROUP BY DATE(created_at)
+                ORDER BY date
+            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
+            
+            labels = [item[0] for item in sales_data] if sales_data else []
+            data = [float(item[1]) for item in sales_data] if sales_data else []
+            
+        elif chart_type == 'orders':
+            # Количество заказов по дням
+            orders_data = db.execute_query('''
+                SELECT 
+                    DATE(created_at) as date,
+                    COUNT(*) as daily_orders
+                FROM orders
+                WHERE DATE(created_at) BETWEEN ? AND ?
+                AND status != 'cancelled'
+                GROUP BY DATE(created_at)
+                ORDER BY date
+            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
+            
+            labels = [item[0] for item in orders_data] if orders_data else []
+            data = [item[1] for item in orders_data] if orders_data else []
+        
+        else:
+            labels = []
+            data = []
+    except Exception as e:
+        print(f"Ошибка получения данных графика: {e}")
+        labels = []
+        data = []
     
     return jsonify({
         'labels': labels,
@@ .. @@
 @app.route('/api/test_telegram')
 @login_required
 def test_telegram():
+    if not telegram_bot:
+        return jsonify({
+            'success': False,
+            'error': 'Telegram бот недоступен'
+        })
+    
     try:
         if telegram_bot.test_connection():
             return jsonify({
                 'success': True,
-                'bot_name': 'Shop Bot'
+                'bot_name': 'Shop Bot',
+                'message': 'Соединение с Telegram API работает'
             })
         else:
             return jsonify({
@@ .. @@
             'error': str(e)
         })

+@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
+@login_required
+def edit_product(product_id):
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('products'))
+    
+    if request.method == 'POST':
+        try:
+            name = request.form['name']
+            description = request.form.get('description', '')
+            price = float(request.form['price'])
+            cost_price = float(request.form.get('cost_price', 0))
+            category_id = int(request.form['category_id'])
+            stock = int(request.form['stock'])
+            
+            # Обработка изображения
+            image_url = request.form.get('current_image_url', '')
+            if 'image_file' in request.files and request.files['image_file'].filename:
+                file = request.files['image_file']
+                if file and allowed_file(file.filename):
+                    filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
+                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
+                    file.save(file_path)
+                    image_url = f'/static/uploads/{filename}'
+            elif request.form.get('image_url'):
+                image_url = request.form['image_url']
+            
+            result = db.execute_query('''
+                UPDATE products 
+                SET name = ?, description = ?, price = ?, cost_price = ?, 
+                    category_id = ?, image_url = ?, stock = ?, updated_at = ?
+                WHERE id = ?
+            ''', (name, description, price, cost_price, category_id, image_url, stock, 
+                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), product_id))
+            
+            if result is not None:
+                if telegram_bot:
+                    telegram_bot.trigger_bot_data_reload()
+                flash(f'Товар "{name}" обновлен!')
+                return redirect(url_for('products'))
+            else:
+                flash('Ошибка обновления товара')
+        except Exception as e:
+            flash(f'Ошибка обновления товара: {e}')
+    
+    # Получаем данные товара
+    try:
+        product = db.get_product_by_id(product_id)
+        categories = db.get_categories()
+        
+        if not product:
+            flash('Товар не найден')
+            return redirect(url_for('products'))
+        
+        return render_template('edit_product.html', product=product, categories=categories or [])
+    except Exception as e:
+        flash(f'Ошибка загрузки товара: {e}')
+        return redirect(url_for('products'))
+
+@app.route('/send_broadcast', methods=['POST'])
+@login_required
+def send_broadcast():
+    if not db or not telegram_bot:
+        flash('Сервисы недоступны')
+        return redirect(url_for('customers'))
+    
+    message = request.form['message']
+    target_audience = request.form['target_audience']
+    
+    try:
+        # Получаем список получателей
+        if target_audience == 'all':
+            recipients = db.execute_query(
+                'SELECT telegram_id, name, language FROM users WHERE is_admin = 0'
+            )
+        elif target_audience == 'active':
+            recipients = db.execute_query('''
+                SELECT DISTINCT u.telegram_id, u.name, u.language
+                FROM users u
+                JOIN orders o ON u.id = o.user_id
+                WHERE u.is_admin = 0 AND o.created_at >= datetime('now', '-30 days')
+            ''')
+        elif target_audience == 'vip':
+            recipients = db.execute_query('''
+                SELECT DISTINCT u.telegram_id, u.name, u.language
+                FROM users u
+                JOIN orders o ON u.id = o.user_id
+                WHERE u.is_admin = 0
+                GROUP BY u.id
+                HAVING SUM(o.total_amount) >= 500
+            ''')
+        else:
+            recipients = []
+        
+        if recipients:
+            success_count, error_count = telegram_bot.send_broadcast(message, recipients)
+            flash(f'Рассылка завершена! Отправлено: {success_count}, Ошибок: {error_count}')
+        else:
+            flash('Нет получателей для рассылки')
+            
+    except Exception as e:
+        flash(f'Ошибка рассылки: {e}')
+    
+    return redirect(url_for('customers'))
+
 @app.route('/export_orders')
 @login_required
 def export_orders():
-    flash('Экспорт заказов будет добавлен в следующей версии')
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('orders'))
+    
+    try:
+        from flask import Response
+        import csv
+        import io
+        
+        # Получаем все заказы
+        orders_data = db.execute_query('''
+            SELECT o.id, o.created_at, u.name, o.total_amount, o.status, o.payment_method
+            FROM orders o
+            JOIN users u ON o.user_id = u.id
+            ORDER BY o.created_at DESC
+        ''')
+        
+        # Создаем CSV
+        output = io.StringIO()
+        writer = csv.writer(output)
+        writer.writerow(['ID заказа', 'Дата', 'Клиент', 'Сумма', 'Статус', 'Оплата'])
+        
+        for order in orders_data or []:
+            writer.writerow([
+                order[0], order[1], order[2], f"${order[3]:.2f}", order[4], order[5]
+            ])
+        
+        output.seek(0)
+        
+        return Response(
+            output.getvalue(),
+            mimetype='text/csv',
+            headers={'Content-Disposition': f'attachment; filename=orders_{datetime.now().strftime("%Y%m%d")}.csv'}
+        )
+    except Exception as e:
+        flash(f'Ошибка экспорта: {e}')
+        return redirect(url_for('orders'))
+
+@app.route('/export_products')
+@login_required
+def export_products():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('products'))
+    
+    try:
+        from flask import Response
+        import csv
+        import io
+        
+        # Получаем все товары
+        products_data = db.execute_query('''
+            SELECT p.id, p.name, p.price, p.stock, c.name as category, p.is_active
+            FROM products p
+            LEFT JOIN categories c ON p.category_id = c.id
+            ORDER BY p.name
+        ''')
+        
+        # Создаем CSV
+        output = io.StringIO()
+        writer = csv.writer(output)
+        writer.writerow(['ID', 'Название', 'Цена', 'Остаток', 'Категория', 'Активен'])
+        
+        for product in products_data or []:
+            writer.writerow([
+                product[0], product[1], f"${product[2]:.2f}", product[3], 
+                product[4] or 'Без категории', 'Да' if product[5] else 'Нет'
+            ])
+        
+        output.seek(0)
+        
+        return Response(
+            output.getvalue(),
+            mimetype='text/csv',
+            headers={'Content-Disposition': f'attachment; filename=products_{datetime.now().strftime("%Y%m%d")}.csv'}
+        )
+    except Exception as e:
+        flash(f'Ошибка экспорта: {e}')
+        return redirect(url_for('products'))
+
+@app.route('/export_customers')
+@login_required
+def export_customers():
+    if not db:
+        flash('База данных недоступна')
+        return redirect(url_for('customers'))
+    
+    try:
+        from flask import Response
+        import csv
+        import io
+        
+        # Получаем всех клиентов
+        customers_data = db.execute_query('''
+            SELECT u.id, u.name, u.phone, u.email, u.created_at,
+                   COUNT(o.id) as orders_count,
+                   COALESCE(SUM(o.total_amount), 0) as total_spent
+            FROM users u
+            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
+            WHERE u.is_admin = 0
+            GROUP BY u.id
+            ORDER BY total_spent DESC
+        ''')
+        
+        # Создаем CSV
+        output = io.StringIO()
+        writer = csv.writer(output)
+        writer.writerow(['ID', 'Имя', 'Телефон', 'Email', 'Дата регистрации', 'Заказов', 'Потрачено'])
+        
+        for customer in customers_data or []:
+            writer.writerow([
+                customer[0], customer[1], customer[2] or '', customer[3] or '', 
+                customer[4], customer[5], f"${customer[6]:.2f}"
+            ])
+        
+        output.seek(0)
+        
+        return Response(
+            output.getvalue(),
+            mimetype='text/csv',
+            headers={'Content-Disposition': f'attachment; filename=customers_{datetime.now().strftime("%Y%m%d")}.csv'}
+        )
+    except Exception as e:
+        flash(f'Ошибка экспорта: {e}')
+        return redirect(url_for('customers'))
+
+@app.errorhandler(404)
+def not_found_error(error):
+    return render_template('error.html', error='Страница не найдена'), 404
+
+@app.errorhandler(500)
+def internal_error(error):
+    return render_template('error.html', error='Внутренняя ошибка сервера'), 500