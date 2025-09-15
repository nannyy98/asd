#!/usr/bin/env python3
"""
Исправление импортов в проекте
"""

import os
import re

def fix_file_imports(filename, fixes):
    """Исправление импортов в файле"""
    if not os.path.exists(filename):
        print(f"⚠️ Файл {filename} не найден")
        return
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for old_import, new_import in fixes.items():
            content = content.replace(old_import, new_import)
        
        if content != original_content:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Исправлены импорты в {filename}")
        else:
            print(f"✅ {filename} - импорты корректны")
            
    except Exception as e:
        print(f"❌ Ошибка исправления {filename}: {e}")

def main():
    """Исправление всех импортов"""
    print("🔧 Исправление импортов...")
    
    # Исправления для разных файлов
    common_fixes = {
        'from utils import format_price': 'from utils import format_price, format_date, get_order_status_emoji',
        'from datetime import datetime': 'from datetime import datetime, timedelta',
    }
    
    files_to_fix = [
        'analytics.py',
        'crm.py', 
        'financial_reports.py',
        'inventory_management.py',
        'marketing_automation.py',
        'notifications.py',
        'promotions.py',
        'logistics.py'
    ]
    
    for filename in files_to_fix:
        if os.path.exists(filename):
            fix_file_imports(filename, common_fixes)
    
    print("\n🎉 Импорты исправлены!")

if __name__ == "__main__":
    main()