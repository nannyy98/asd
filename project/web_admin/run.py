#!/usr/bin/env python3
"""
Запуск веб-панели администратора v2.0
"""

import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from core.config import config

if __name__ == '__main__':
    print("🌐 Запуск веб-панели администратора...")
    print(f"📱 URL: http://localhost:5000")
    print(f"👤 Логин: {config.bot.admin_name}")
    print(f"🔑 Пароль: admin123")
    print("🔗 Интеграция с Telegram ботом активна")
    
    app.run(
        debug=config.debug,
        host='0.0.0.0',
        port=5000
    )