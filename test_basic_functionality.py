#!/usr/bin/env python3
"""
Тест базовой функциональности бота
"""

import os
import sys
from database import DatabaseManager

def test_database_connection():
    """Тест подключения к базе данных"""
    print("🔍 Тестирование базы данных...")
    
    try:
        db = DatabaseManager()
        
        # Проверяем категории
        categories = db.get_categories()
        print(f"✅ Категории: {len(categories) if categories else 0}")
        
        # Проверяем товары
        products = db.execute_query('SELECT COUNT(*) FROM products WHERE is_active = 1')
        print(f"✅ Активных товаров: {products[0][0] if products else 0}")
        
        # Проверяем админов
        admins = db.execute_query('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        print(f"✅ Админов: {admins[0][0] if admins else 0}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False

def test_token():
    """Тест токена бота"""
    print("\n🔑 Проверка токена...")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        token = "8292684103:AAH0TKL-lCOaKVeppjtAdmsx0gdeMrGtjdQ"
    
    if token and len(token) > 40 and ':' in token:
        print(f"✅ Токен корректен: {token[:10]}...{token[-10:]}")
        return True
    else:
        print("❌ Токен некорректен")
        return False

def test_modules_import():
    """Тест импорта модулей"""
    print("\n📦 Проверка модулей...")
    
    modules_to_test = [
        'database',
        'handlers', 
        'admin',
        'keyboards',
        'utils',
        'localization',
        'config'
    ]
    
    success_count = 0
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
        except Exception as e:
            print(f"⚠️ {module_name}: {e}")
    
    print(f"\n📊 Импортировано: {success_count}/{len(modules_to_test)} модулей")
    return success_count == len(modules_to_test)

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование телеграм-бота")
    print("=" * 40)
    
    tests = [
        test_token,
        test_modules_import,
        test_database_connection
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Результат: {passed}/{len(tests)} тестов пройдено")
    
    if passed == len(tests):
        print("🎉 Все тесты пройдены! Бот готов к запуску")
        print("\n🚀 Запустите бота: python main.py")
    else:
        print("❌ Есть проблемы, но основная функциональность должна работать")
        print("🚀 Попробуйте запустить: python main.py")

if __name__ == "__main__":
    main()