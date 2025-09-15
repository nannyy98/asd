#!/usr/bin/env python3
"""
Скрипт для тестирования основных функций бота
"""

import sqlite3
import os

def test_database():
    """Тестирование базы данных"""
    print("🔍 Проверка базы данных...")
    
    if not os.path.exists('shop_bot.db'):
        print("❌ База данных не найдена")
        return False
    
    try:
        conn = sqlite3.connect('shop_bot.db')
        cursor = conn.cursor()
        
        # Проверяем категории
        cursor.execute('SELECT id, name, emoji FROM categories')
        categories = cursor.fetchall()
        print(f"✅ Категории ({len(categories)}):")
        for cat in categories:
            print(f"   ID: {cat[0]}, Название: '{cat[1]}', Эмодзи: '{cat[2]}'")
        
        # Проверяем товары
        cursor.execute('SELECT id, name, price, category_id, stock, is_active FROM products')
        products = cursor.fetchall()
        print(f"\n✅ Товары ({len(products)}):")
        for prod in products[:5]:  # Показываем первые 5
            print(f"   ID: {prod[0]}, Название: '{prod[1]}', Цена: ${prod[2]}, Категория: {prod[3]}, Остаток: {prod[4]}, Активен: {prod[5]}")
        
        # Проверяем админов
        cursor.execute('SELECT telegram_id, name, is_admin FROM users WHERE is_admin = 1')
        admins = cursor.fetchall()
        print(f"\n✅ Админы ({len(admins)}):")
        for admin in admins:
            print(f"   Telegram ID: {admin[0]}, Имя: '{admin[1]}'")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки базы: {e}")
        return False

def test_token():
    """Проверка токена бота"""
    print("\n🔑 Проверка токена...")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
        return False
    
    if len(token) < 40:
        print("❌ Токен слишком короткий")
        return False
    
    if ':' not in token:
        print("❌ Неверный формат токена")
        return False
    
    print(f"✅ Токен найден: {token[:10]}...{token[-10:]}")
    return True

def test_admin_config():
    """Проверка конфигурации админа"""
    print("\n👤 Проверка конфигурации админа...")
    
    admin_id = os.getenv('ADMIN_TELEGRAM_ID')
    admin_name = os.getenv('ADMIN_NAME', 'Admin')
    
    if not admin_id:
        print("❌ ADMIN_TELEGRAM_ID не установлен")
        return False
    
    try:
        admin_id = int(admin_id)
        print(f"✅ Админ ID: {admin_id}")
        print(f"✅ Админ имя: {admin_name}")
        return True
    except ValueError:
        print(f"❌ Неверный формат ADMIN_TELEGRAM_ID: {admin_id}")
        return False

def fix_common_issues():
    """Исправление частых проблем"""
    print("\n🔧 Исправление частых проблем...")
    
    try:
        conn = sqlite3.connect('shop_bot.db')
        cursor = conn.cursor()
        
        # Проверяем и исправляем товары без категорий
        cursor.execute('SELECT COUNT(*) FROM products WHERE category_id IS NULL')
        orphan_products = cursor.fetchone()[0]
        
        if orphan_products > 0:
            print(f"⚠️ Найдено {orphan_products} товаров без категории")
            cursor.execute('UPDATE products SET category_id = 1 WHERE category_id IS NULL')
            print("✅ Товары привязаны к категории 'Электроника'")
        
        # Проверяем активность товаров
        cursor.execute('SELECT COUNT(*) FROM products WHERE is_active = 0')
        inactive_products = cursor.fetchone()[0]
        
        if inactive_products > 0:
            print(f"⚠️ Найдено {inactive_products} неактивных товаров")
            cursor.execute('UPDATE products SET is_active = 1')
            print("✅ Все товары активированы")
        
        # Проверяем остатки товаров
        cursor.execute('SELECT COUNT(*) FROM products WHERE stock <= 0')
        out_of_stock = cursor.fetchone()[0]
        
        if out_of_stock > 0:
            print(f"⚠️ Найдено {out_of_stock} товаров без остатка")
            cursor.execute('UPDATE products SET stock = 10 WHERE stock <= 0')
            print("✅ Остатки товаров восстановлены")
        
        conn.commit()
        conn.close()
        
        print("✅ Проблемы исправлены")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка исправления: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 Тестирование телеграм-бота\n")
    
    # Загружаем переменные окружения
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env файл загружен")
    except ImportError:
        print("⚠️ python-dotenv не установлен, используем системные переменные")
    
    # Запускаем тесты
    tests = [
        test_token,
        test_admin_config,
        test_database,
        fix_common_issues
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
        print("❌ Есть проблемы, исправьте их перед запуском")

if __name__ == "__main__":
    main()