"""
Веб-панель администратора v2.0
Современная, безопасная и красивая панель управления
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import config
from core.logger import logger
from database.manager import DatabaseManager
from services.analytics_service import AnalyticsService

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-in-production')

# Инициализация
db = DatabaseManager()
analytics = AnalyticsService(db)

# Добавляем config в контекст шаблонов
@app.context_processor
def inject_config():
    return {'app_config': config}

def login_required(f):
    """Декоратор для проверки авторизации"""
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Простая проверка (в продакшене использовать хеширование)
        admin_name = config.bot.admin_name
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        if username == admin_name and password == admin_password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Неверные учетные данные')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Главная панель"""
    try:
        # Получаем полную статистику
        dashboard_stats = analytics.get_dashboard_stats()
        
        # Последние заказы
        recent_orders = db.execute_query('''
            SELECT o.id, o.total_amount, o.status, o.created_at, u.name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 10
        ''')
        
        # Получаем аналитику товаров
        product_analytics = analytics.get_product_analytics()
        
        # Тренды продаж
        sales_trends = analytics.get_sales_trends(7)
        
        return render_template('dashboard.html',
                             dashboard_stats=dashboard_stats,
                             recent_orders=recent_orders or [],
                             top_products=product_analytics['top_products'][:5],
                             sales_trends=sales_trends)
                             
    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        flash('Ошибка загрузки данных')
        return render_template('dashboard.html',
                             dashboard_stats={},
                             recent_orders=[],

@app.route('/orders')
@login_required
def orders():
    """Страница заказов"""
    try:
        orders_data = db.execute_query('''
            SELECT o.id, o.total_amount, o.status, o.created_at, u.name, u.phone, u.email, o.delivery_address, o.payment_method
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 50
        ''')
        
        return render_template('orders.html', orders=orders_data or [])
    except Exception as e:
        logger.error(f"Ошибка загрузки заказов: {e}")
        return render_template('orders.html', orders=[])

@app.route('/order_detail/<int:order_id>')
@login_required
def order_detail(order_id):
    """Детали заказа"""
    try:
        order_data = db.get_order_details(order_id)
        if not order_data:
            flash('Заказ не найден')
            return redirect(url_for('orders'))
        
        # Получаем информацию о клиенте
        user_id = order_data['order'][1]
        customer_info = db.execute_query(
            'SELECT name, phone, email, created_at FROM users WHERE id = ?',
            (user_id,)
        )
        customer_info = customer_info[0] if customer_info else None
        
        return render_template('order_detail.html', 
                             order_data=order_data,
                             customer_info=customer_info)
    except Exception as e:
        logger.error(f"Ошибка загрузки деталей заказа: {e}")
        flash('Ошибка загрузки заказа')
        return redirect(url_for('orders'))

@app.route('/products')
@login_required
def products():
    """Страница товаров"""
    try:
        # Получаем категории для фильтра
        categories = db.get_categories()
        
        # Получаем товары с информацией о категориях
        products_data = db.execute_query('''
            SELECT p.id, p.name, p.price, p.stock, p.is_active, c.name as category_name, 
                   p.sales_count, p.views
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.created_at DESC
        ''')
        
        return render_template('products.html', 
                             products=products_data or [], 
                             categories=categories or [])
    except Exception as e:
        logger.error(f"Ошибка загрузки товаров: {e}")
        return render_template('products.html', products=[], categories=[])

@app.route('/customers')
@login_required
def customers():
    """Страница клиентов"""
    try:
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = 20
        offset = (page - 1) * per_page
        
        # Поиск клиентов
        if search:
            customers_data = db.execute_query('''
                SELECT u.id, u.name, u.phone, u.email, u.created_at,
                       COUNT(o.id) as orders_count,
                       COALESCE(SUM(o.total_amount), 0) as total_spent,
                       MAX(o.created_at) as last_order
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
                WHERE u.is_admin = 0 AND (
                    u.name LIKE ? OR 
                    u.phone LIKE ? OR 
                    u.email LIKE ?
                )
                GROUP BY u.id, u.name, u.phone, u.email, u.created_at
                ORDER BY total_spent DESC
                LIMIT ? OFFSET ?
            ''', (f'%{search}%', f'%{search}%', f'%{search}%', per_page, offset))
        else:
            customers_data = db.execute_query('''
                SELECT u.id, u.name, u.phone, u.email, u.created_at,
                       COUNT(o.id) as orders_count,
                       COALESCE(SUM(o.total_amount), 0) as total_spent,
                       MAX(o.created_at) as last_order
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
                WHERE u.is_admin = 0
                GROUP BY u.id, u.name, u.phone, u.email, u.created_at
                ORDER BY total_spent DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
        
        # Подсчет общего количества для пагинации
        total_count = db.execute_query('''
            SELECT COUNT(*) FROM users WHERE is_admin = 0
        ''')[0][0] if db.execute_query('SELECT COUNT(*) FROM users WHERE is_admin = 0') else 0
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('customers.html', 
                             customers=customers_data or [], 
                             search=search,
                             current_page=page,
                             total_pages=total_pages)
    except Exception as e:
        logger.error(f"Ошибка загрузки клиентов: {e}")
        return render_template('customers.html', customers=[], search='', current_page=1, total_pages=1)

@app.route('/export_customers')
@login_required
def export_customers():
    """Экспорт клиентов в CSV"""
    try:
        import csv
        import io
        from flask import make_response
        
        customers_data = db.execute_query('''
            SELECT u.id, u.name, u.phone, u.email, u.language, u.created_at,
                   COUNT(o.id) as orders_count,
                   COALESCE(SUM(o.total_amount), 0) as total_spent,
                   MAX(o.created_at) as last_order
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
            WHERE u.is_admin = 0
            GROUP BY u.id, u.name, u.phone, u.email, u.language, u.created_at
            ORDER BY total_spent DESC
        ''')
        
        # Создаем CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            'ID', 'Имя', 'Телефон', 'Email', 'Язык', 'Дата регистрации',
            'Количество заказов', 'Потрачено', 'Последний заказ'
        ])
        
        # Данные
        for customer in customers_data or []:
            writer.writerow([
                customer[0],  # ID
                customer[1],  # Имя
                customer[2] or 'Не указан',  # Телефон
                customer[3] or 'Не указан',  # Email
                customer[4],  # Язык
                customer[5][:10] if customer[5] else '',  # Дата регистрации
                customer[6],  # Количество заказов
                f"${customer[7]:.2f}",  # Потрачено
                customer[8][:10] if customer[8] else 'Нет заказов'  # Последний заказ
            ])
        
        # Создаем ответ
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=customers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:

@app.route('/analytics')
@login_required
def analytics_page():
    """Страница аналитики"""
    try:
        period = request.args.get('period', '30')
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(period))
        
        sales_report = analytics.get_sales_report(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Получаем дополнительную аналитику
        product_analytics = analytics.get_product_analytics()
        sales_trends = analytics.get_sales_trends(int(period))
        
        return render_template('analytics.html',
                             sales_report=sales_report,
                             product_analytics=product_analytics,
                             sales_trends=sales_trends,
                             period=period)
    except Exception as e:
        logger.error(f"Ошибка загрузки аналитики: {e}")
        return render_template('analytics.html', 
                             sales_report={'summary': (0, 0, 0, 0), 'top_products': []},
                             product_analytics={'top_products': [], 'category_stats': []},
                             sales_trends={'daily_sales': []},
                             period='30')

@app.route('/api/chart_data')
@login_required
def chart_data():
    """API для данных графиков"""
    chart_type = request.args.get('type', 'sales')
    period = int(request.args.get('period', 30))
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    try:
        if chart_type == 'sales':
            data = db.execute_query('''
                SELECT 
                    DATE(created_at) as date,
                    COALESCE(SUM(total_amount), 0) as daily_revenue
                FROM orders
                WHERE DATE(created_at) BETWEEN ? AND ?
                AND status != 'cancelled'
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            labels = [item[0] for item in data] if data else []
            values = [float(item[1]) for item in data] if data else []
            
        elif chart_type == 'orders':
            data = db.execute_query('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as daily_orders
                FROM orders
                WHERE DATE(created_at) BETWEEN ? AND ?
                AND status != 'cancelled'
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            labels = [item[0] for item in data] if data else []
            values = [item[1] for item in data] if data else []
        else:
            labels = []
            values = []
        
        return jsonify({
            'labels': labels,
            'data': values
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения данных графика: {e}")
        return jsonify({'labels': [], 'data': []})

@app.route('/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    """Обновление статуса заказа"""
    try:
        order_id = request.form['order_id']
        status = request.form['status']
        
        db.update_order_status(order_id, status)
        flash(f'Статус заказа #{order_id} обновлен')
        
    except Exception as e:
        logger.error(f"Ошибка обновления статуса: {e}")
        flash('Ошибка обновления статуса')
    
    return redirect(url_for('orders'))

@app.route('/crm')
@login_required
def crm():
    """CRM аналитика"""
    try:
        crm_data = analytics.get_crm_analytics()
        return render_template('crm.html', **crm_data)
    except Exception as e:
        logger.error(f"Ошибка загрузки CRM: {e}")
        return render_template('crm.html', segments={}, at_risk_customers=[])

if __name__ == '__main__':
    app.run(debug=config.debug, host='0.0.0.0', port=5000)