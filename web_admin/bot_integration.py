"""

import sys
import os
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def trigger_bot_data_reload(self):
        """Сигнал боту о необходимости перезагрузки данных"""
        try:
            # Создаем файл-флаг для бота
            import time
            update_flag_file = '../data_update_flag.txt'
            with open(update_flag_file, 'w') as f:
                f.write(str(time.time()))
            print(f"✅ Флаг обновления создан: {time.time()}")
            return True
        except Exception as e:
            print(f"Ошибка создания флага обновления: {e}")
            return False
    
    def test_connection(self):
        """Тестирование соединения с Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            with urllib.request.urlopen(url) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('ok'):
                    print(f"✅ Telegram API работает: {result.get('result', {}).get('username', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Telegram API ошибка: {result}")
                    return False
        except Exception as e:
            print(f"Ошибка тестирования соединения: {e}")
            return False