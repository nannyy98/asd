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