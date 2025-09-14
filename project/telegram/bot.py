"""
Основной класс Telegram бота
"""

import json
import urllib.request
import urllib.parse
import time
from typing import Optional, Dict, Any

from core.logger import logger
from core.exceptions import ShopBotException
from core.config import config

class TelegramBot:
    """Основной класс для работы с Telegram API"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.running = True
    
    def send_message(self, chat_id: int, text: str, 
                    reply_markup: Optional[Dict] = None) -> Optional[Dict]:
        """Отправка сообщения"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        return self._make_request(url, data)
    
    def send_photo(self, chat_id: int, photo_url: str, caption: str = "", 
                  reply_markup: Optional[Dict] = None) -> Optional[Dict]:
        """Отправка фото"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        return self._make_request(url, data)
    
    def edit_message_reply_markup(self, chat_id: int, message_id: int, 
                                 reply_markup: Dict) -> bool:
        """Редактирование клавиатуры сообщения"""
        time.sleep(240)  # Задержка 4 минуты для стабильности соединения
        url = f"{self.base_url}/editMessageReplyMarkup"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reply_markup': json.dumps(reply_markup)
        }
        
        result = self._make_request(url, data)
        return result and result.get('ok', False)
    
    def get_updates(self) -> Optional[Dict]:
        """Получение обновлений"""
        url = f"{self.base_url}/getUpdates"
        params = {'offset': self.offset, 'timeout': 30}
        
        try:
            url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url_with_params, timeout=35) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Ошибка получения обновлений: {e}")
            return None
    
    def _make_request(self, url: str, data: Dict) -> Optional[Dict]:
        """Выполнение HTTP запроса к Telegram API"""
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if not result.get('ok'):
                    logger.warning(f"Telegram API error: {result}")
                
                return result
                
        except Exception as e:
            logger.error(f"Ошибка запроса к Telegram API: {e}")
            return None
    
    def stop(self):
        """Остановка бота"""
        self.running = False
        logger.info("Бот остановлен")