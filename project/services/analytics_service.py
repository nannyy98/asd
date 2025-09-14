"""
Сервис аналитики
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from core.logger import logger
from core.utils import format_price, format_date

class AnalyticsService:
    """Сервис аналитики и отчетности"""
    
    def __init__(self, db):
        self.db = db
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Статистика для главной панели"""
        try:
            # Общая статистика
            total_stats = self.db.execute_query('''
                SELECT 
                    COUNT(DISTINCT u.id) as total_users,
                    COUNT(DISTINCT CASE WHEN o.id IS NOT NULL THEN u.id END) as buyers,
                    COUNT(o.id) as total_orders,
                    COALESCE(SUM(o.total_amount), 0) as total_revenue,
                    COALESCE(AVG(o.total_amount), 0) as avg_order_value
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
                WHERE u.is_admin = 0
            ''')
            
            # Статистика за сегодня
            today = datetime.now().strftime('%Y-%m-%d')
            today_stats = self.db.execute_query('''
                SELECT 
                    COUNT(DISTINCT u.id) as new_users_today,
                    COUNT(o.id) as orders_today,
                    COALESCE(SUM(o.total_amount), 0) as revenue_today
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id AND DATE(o.created_at) = ? AND o.status != 'cancelled'
                WHERE DATE(u.created_at) = ?
            ''', (today, today))
            
            # Активные пользователи (за последние 7 дней)
            active_users = self.db.execute_query('''
                SELECT COUNT(DISTINCT user_id) as active_users
                FROM orders 
                WHERE created_at >= datetime('now', '-7 days')
                AND status != 'cancelled'
            ''')
            
            # Конверсия
            total = total_stats[0] if total_stats else (0, 0, 0, 0, 0)
            today = today_stats[0] if today_stats else (0, 0, 0)
            active = active_users[0][0] if active_users else 0
            
            conversion_rate = (total[1] / total[0] * 100) if total[0] > 0 else 0
            
            return {
                'total_users': total[0],
                'buyers': total[1],
                'total_orders': total[2],
                'total_revenue': total[3],
                'avg_order_value': total[4],
                'new_users_today': today[0],
                'orders_today': today[1],
                'revenue_today': today[2],
                'active_users': active,
                'conversion_rate': conversion_rate
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики дашборда: {e}")
            return {
                'total_users': 0, 'buyers': 0, 'total_orders': 0,
                'total_revenue': 0, 'avg_order_value': 0,
                'new_users_today': 0, 'orders_today': 0, 'revenue_today': 0,
                'active_users': 0, 'conversion_rate': 0
            }
    
    def get_crm_analytics(self) -> Dict[str, Any]:
        """CRM аналитика клиентов"""
        try:
            # Сегментация клиентов по RFM
            customer_segments = self.db.execute_query('''
                WITH customer_stats AS (
                    SELECT 
                        u.id,
                        u.name,
                        COUNT(o.id) as frequency,
                        COALESCE(SUM(o.total_amount), 0) as monetary,
                        COALESCE(MAX(julianday('now') - julianday(o.created_at)), 999) as recency,
                        MAX(o.created_at) as last_order
                    FROM users u
                    LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
                    WHERE u.is_admin = 0
                    GROUP BY u.id, u.name
                )
                SELECT 
                    id, name, frequency, monetary, recency, last_order,
                    CASE 
                        WHEN frequency >= 5 AND monetary >= 500 AND recency <= 30 THEN 'champions'
                        WHEN frequency >= 3 AND monetary >= 200 AND recency <= 60 THEN 'loyal'
                        WHEN frequency >= 2 AND monetary >= 100 AND recency <= 90 THEN 'potential'
                        WHEN frequency = 0 THEN 'new'
                        WHEN recency > 90 AND frequency >= 2 THEN 'at_risk'
                        ELSE 'need_attention'
                    END as segment
                FROM customer_stats
                ORDER BY monetary DESC
            ''')
            
            # Группируем по сегментам
            segments = {
                'champions': [],
                'loyal': [],
                'potential': [],
                'new': [],
                'at_risk': [],
                'need_attention': []
            }
            
            for customer in customer_segments or []:
                segment = customer[6]
                segments[segment].append(customer)
            
            # Клиенты в зоне риска (не покупали > 60 дней)
            at_risk_customers = self.db.execute_query('''
                SELECT 
                    u.id, u.name, u.phone, 
                    MAX(o.created_at) as last_order,
                    julianday('now') - julianday(MAX(o.created_at)) as days_since_last,
                    COUNT(o.id) as total_orders,
                    COALESCE(SUM(o.total_amount), 0) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
                WHERE u.is_admin = 0
                GROUP BY u.id, u.name, u.phone
                HAVING MAX(o.created_at) IS NOT NULL 
                AND julianday('now') - julianday(MAX(o.created_at)) > 60
                ORDER BY days_since_last DESC
                LIMIT 20
            ''')
            
            return {
                'segments': segments,
                'at_risk_customers': at_risk_customers or []
            }
            
        except Exception as e:
            logger.error(f"Ошибка CRM аналитики: {e}")
            return {
                'segments': {
                    'champions': [], 'loyal': [], 'potential': [],
                    'new': [], 'at_risk': [], 'need_attention': []
                },
                'at_risk_customers': []
            }
    
    def get_product_analytics(self) -> Dict[str, Any]:
        """Аналитика товаров"""
        try:
            # Самые популярные товары
            top_products = self.db.execute_query('''
                SELECT 
                    p.name,
                    SUM(oi.quantity) as total_sold,
                    SUM(oi.quantity * oi.price) as revenue,
                    COUNT(DISTINCT o.user_id) as unique_buyers,
                    p.views,
                    ROUND(SUM(oi.quantity) * 100.0 / NULLIF(p.views, 0), 2) as conversion_rate
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'cancelled'
                WHERE p.is_active = 1
                GROUP BY p.id, p.name, p.views
                ORDER BY revenue DESC
                LIMIT 10
            ''')
            
            # Товары с низкой конверсией
            low_conversion = self.db.execute_query('''
                SELECT 
                    p.name,
                    p.views,
                    COALESCE(SUM(oi.quantity), 0) as sales,
                    ROUND(COALESCE(SUM(oi.quantity), 0) * 100.0 / NULLIF(p.views, 0), 2) as conversion_rate,
                    p.price
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'cancelled'
                WHERE p.is_active = 1 AND p.views > 10
                GROUP BY p.id, p.name, p.views, p.price
                HAVING conversion_rate < 5 OR conversion_rate IS NULL
                ORDER BY p.views DESC
                LIMIT 10
            ''')
            
            # Категории по популярности
            category_stats = self.db.execute_query('''
                SELECT 
                    c.name,
                    c.emoji,
                    COUNT(DISTINCT p.id) as products_count,
                    COALESCE(SUM(oi.quantity), 0) as total_sold,
                    COALESCE(SUM(oi.quantity * oi.price), 0) as revenue
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'cancelled'
                WHERE c.is_active = 1
                GROUP BY c.id, c.name, c.emoji
                ORDER BY revenue DESC
            ''')
            
            return {
                'top_products': top_products or [],
                'low_conversion': low_conversion or [],
                'category_stats': category_stats or []
            }
            
        except Exception as e:
            logger.error(f"Ошибка аналитики товаров: {e}")
            return {
                'top_products': [],
                'low_conversion': [],
                'category_stats': []
            }
    
    def get_sales_trends(self, days: int = 30) -> Dict[str, Any]:
        """Тренды продаж"""
        try:
            # Продажи по дням
            daily_sales = self.db.execute_query('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as orders,
                    COALESCE(SUM(total_amount), 0) as revenue,
                    COUNT(DISTINCT user_id) as unique_customers
                FROM orders
                WHERE created_at >= datetime('now', '-{} days')
                AND status != 'cancelled'
                GROUP BY DATE(created_at)
                ORDER BY date
            '''.format(days))
            
            # Продажи по часам (за последние 7 дней)
            hourly_sales = self.db.execute_query('''
                SELECT 
                    CAST(strftime('%H', created_at) AS INTEGER) as hour,
                    COUNT(*) as orders,
                    COALESCE(SUM(total_amount), 0) as revenue
                FROM orders
                WHERE created_at >= datetime('now', '-7 days')
                AND status != 'cancelled'
                GROUP BY hour
                ORDER BY hour
            ''')
            
            # Продажи по дням недели
            weekly_sales = self.db.execute_query('''
                SELECT 
                    CASE strftime('%w', created_at)
                        WHEN '0' THEN 'Воскресенье'
                        WHEN '1' THEN 'Понедельник'
                        WHEN '2' THEN 'Вторник'
                        WHEN '3' THEN 'Среда'
                        WHEN '4' THEN 'Четверг'
                        WHEN '5' THEN 'Пятница'
                        WHEN '6' THEN 'Суббота'
                    END as day_name,
                    strftime('%w', created_at) as day_num,
                    COUNT(*) as orders,
                    COALESCE(SUM(total_amount), 0) as revenue
                FROM orders
                WHERE created_at >= datetime('now', '-30 days')
                AND status != 'cancelled'
                GROUP BY strftime('%w', created_at)
                ORDER BY day_num
            ''')
            
            return {
                'daily_sales': daily_sales or [],
                'hourly_sales': hourly_sales or [],
                'weekly_sales': weekly_sales or []
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения трендов: {e}")
            return {
                'daily_sales': [],
                'hourly_sales': [],
                'weekly_sales': []
            }
    def get_sales_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Отчет по продажам"""
        try:
            # Основная статистика
            sales_data = self.db.execute_query('''
                SELECT 
                    COUNT(*) as orders_count,
                    COALESCE(SUM(total_amount), 0) as revenue,
                    COALESCE(AVG(total_amount), 0) as avg_order_value,
                    COUNT(DISTINCT user_id) as unique_customers
                FROM orders 
                WHERE DATE(created_at) BETWEEN ? AND ?
                AND status != 'cancelled'
            ''', (start_date, end_date))
            
            # Топ товары
            top_products = self.db.execute_query('''
                SELECT 
                    p.name,
                    SUM(oi.quantity) as units_sold,
                    SUM(oi.quantity * oi.price) as revenue
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE DATE(o.created_at) BETWEEN ? AND ?
                AND o.status != 'cancelled'
                GROUP BY p.id, p.name
                ORDER BY revenue DESC
                LIMIT 10
            ''', (start_date, end_date))
            
            # Продажи по дням
            daily_sales = self.db.execute_query('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as orders,
                    SUM(total_amount) as revenue
                FROM orders
                WHERE DATE(created_at) BETWEEN ? AND ?
                AND status != 'cancelled'
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (start_date, end_date))
            
            return {
                'period': f"{start_date} - {end_date}",
                'summary': sales_data[0] if sales_data else (0, 0, 0, 0),
                'top_products': top_products or [],
                'daily_sales': daily_sales or []
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания отчета по продажам: {e}")
            return {
                'period': f"{start_date} - {end_date}",
                'summary': (0, 0, 0, 0),
                'top_products': [],
                'daily_sales': []
            }
    
    def get_customer_analytics(self) -> Dict[str, Any]:
        """Аналитика клиентов"""
        try:
            # Сегментация клиентов
            customer_segments = self.db.execute_query('''
                SELECT 
                    CASE 
                        WHEN total_spent >= 1000 THEN 'VIP'
                        WHEN total_spent >= 500 THEN 'Premium'
                        WHEN total_spent >= 100 THEN 'Regular'
                        WHEN total_spent > 0 THEN 'New'
                        ELSE 'Inactive'
                    END as segment,
                    COUNT(*) as count,
                    AVG(total_spent) as avg_spent
                FROM (
                    SELECT 
                        u.id,
                        COALESCE(SUM(o.total_amount), 0) as total_spent
                    FROM users u
                    LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
                    WHERE u.is_admin = 0
                    GROUP BY u.id
                ) customer_stats
                GROUP BY segment
                ORDER BY avg_spent DESC
            ''')
            
            # Активность по дням недели
            weekly_activity = self.db.execute_query('''
                SELECT 
                    CASE strftime('%w', created_at)
                        WHEN '0' THEN 'Воскресенье'
                        WHEN '1' THEN 'Понедельник'
                        WHEN '2' THEN 'Вторник'
                        WHEN '3' THEN 'Среда'
                        WHEN '4' THEN 'Четверг'
                        WHEN '5' THEN 'Пятница'
                        WHEN '6' THEN 'Суббота'
                    END as day_name,
                    COUNT(*) as orders_count,
                    SUM(total_amount) as revenue
                FROM orders
                WHERE created_at >= datetime('now', '-30 days')
                AND status != 'cancelled'
                GROUP BY strftime('%w', created_at)
                ORDER BY strftime('%w', created_at)
            ''')
            
            return {
                'customer_segments': customer_segments or [],
                'weekly_activity': weekly_activity or []
            }
            
        except Exception as e:
            logger.error(f"Ошибка аналитики клиентов: {e}")
            return {
                'customer_segments': [],
                'weekly_activity': []
            }
    
    def get_product_performance(self) -> Dict[str, Any]:
        """Анализ эффективности товаров"""
        try:
            # Топ товары по продажам
            top_selling = self.db.execute_query('''
                SELECT 
                    p.name,
                    p.price,
                    p.stock,
                    SUM(oi.quantity) as total_sold,
                    SUM(oi.quantity * oi.price) as revenue,
                    p.views,
                    ROUND(SUM(oi.quantity) * 100.0 / p.views, 2) as conversion_rate
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'cancelled'
                WHERE p.is_active = 1
                GROUP BY p.id, p.name, p.price, p.stock, p.views
                ORDER BY revenue DESC
                LIMIT 20
            ''')
            
            # Товары с низкой конверсией
            low_conversion = self.db.execute_query('''
                SELECT 
                    p.name,
                    p.views,
                    COALESCE(SUM(oi.quantity), 0) as sales,
                    ROUND(COALESCE(SUM(oi.quantity), 0) * 100.0 / NULLIF(p.views, 0), 2) as conversion_rate
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'cancelled'
                WHERE p.is_active = 1 AND p.views > 10
                GROUP BY p.id, p.name, p.views
                HAVING conversion_rate < 5
                ORDER BY p.views DESC
                LIMIT 10
            ''')
            
            return {
                'top_selling': top_selling or [],
                'low_conversion': low_conversion or []
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа товаров: {e}")
            return {
                'top_selling': [],
                'low_conversion': []
            }
    
    def format_sales_report(self, report: Dict[str, Any]) -> str:
        """Форматирование отчета по продажам"""
        if not report or not report['summary']:
            return "📊 Нет данных для отчета"
        
        summary = report['summary']
        
        text = f"📊 <b>Отчет по продажам</b>\n"
        text += f"📅 Период: {report['period']}\n\n"
        text += f"📦 Заказов: {summary[0]}\n"
        text += f"💰 Выручка: {format_price(summary[1])}\n"
        text += f"💳 Средний чек: {format_price(summary[2])}\n"
        text += f"👥 Уникальных клиентов: {summary[3]}\n\n"
        
        if report['top_products']:
            text += f"🏆 <b>Топ товары:</b>\n"
            for i, product in enumerate(report['top_products'][:5], 1):
                text += f"{i}. {product[0]} - {product[1]} шт. ({format_price(product[2])})\n"
        
        return text