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
        # Статистика за сегодня
        today = datetime.now().strftime('%Y-%m-%d')
        today_stats = db.execute_query('''
            SELECT 
                COUNT(*) as orders_today,
                COALESCE(SUM(total_amount), 0) as revenue_today,
                COUNT(DISTINCT user_id) as customers_today
            FROM orders 
            WHERE DATE(created_at) = ? AND status != 'cancelled'
        ''', (today,))
        
        # Общая статистика
        total_stats = db.execute_query('''
            SELECT 
                COUNT(DISTINCT u.id) as total_customers,
                COUNT(o.id) as total_orders,
                COALESCE(SUM(o.total_amount), 0) as total_revenue
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
            WHERE u.is_admin = 0
        ''')
        
        # Последние заказы
        recent_orders = db.execute_query('''
            SELECT o.id, o.total_amount, o.status, o.created_at, u.name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 10
        ''')
        
        # Топ товары
        top_products = db.execute_query('''
            SELECT p.name, SUM(oi.quantity) as sold, SUM(oi.quantity * oi.price) as revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at >= date('now', '-7 days') AND o.status != 'cancelled'
            GROUP BY p.id, p.name
            ORDER BY revenue DESC
            LIMIT 5
        ''')
        
        return render_template('dashboard.html',
                             today_stats=today_stats[0] if today_stats else (0, 0, 0),
                             total_stats=total_stats[0] if total_stats else (0, 0, 0),
                             recent_orders=recent_orders or [],
                             top_products=top_products or [])
                             
    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        flash('Ошибка загрузки данных')
        return render_template('dashboard.html',
                             today_stats=(0, 0, 0),
                             total_stats=(0, 0, 0),
                             recent_orders=[],
                             top_products=[])

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

if __name__ == '__main__':
    app.run(debug=config.debug, host='0.0.0.0', port=5000)