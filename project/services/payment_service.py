"""
Сервис платежей
"""

from typing import Dict, Any, Optional
from decimal import Decimal

from core.logger import logger
from core.exceptions import PaymentError
from core.utils import format_price

class PaymentService:
    """Сервис обработки платежей"""
    
    def __init__(self):
        self.providers = {
            'stripe': StripeProvider(),
            'paypal': PayPalProvider(),
            'payme': PaymeProvider(),
            'click': ClickProvider()
        }
    
    def create_payment(self, provider: str, amount: Decimal, order_id: int, 
                      user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создание платежа"""
        if provider not in self.providers:
            raise PaymentError(f"Неподдерживаемый провайдер: {provider}")
        
        try:
            return self.providers[provider].create_payment(amount, order_id, user_data)
        except Exception as e:
            logger.error(f"Ошибка создания платежа {provider}: {e}")
            raise PaymentError(f"Payment creation failed: {e}")
    
    def verify_payment(self, provider: str, payment_data: Dict[str, Any]) -> bool:
        """Проверка статуса платежа"""
        if provider not in self.providers:
            return False
        
        try:
            return self.providers[provider].verify_payment(payment_data)
        except Exception as e:
            logger.error(f"Ошибка проверки платежа {provider}: {e}")
            return False

class BasePaymentProvider:
    """Базовый класс провайдера платежей"""
    
    def create_payment(self, amount: Decimal, order_id: int, 
                      user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание платежа"""
        raise NotImplementedError
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        """Проверка платежа"""
        raise NotImplementedError

class StripeProvider(BasePaymentProvider):
    """Провайдер Stripe"""
    
    def create_payment(self, amount: Decimal, order_id: int, 
                      user_data: Dict[str, Any]) -> Dict[str, Any]:
        amount_cents = int(amount * 100)
        
        return {
            'url': f"https://checkout.stripe.com/pay/example_{order_id}",
            'provider': 'stripe',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        return payment_data.get('status') == 'succeeded'

class PayPalProvider(BasePaymentProvider):
    """Провайдер PayPal"""
    
    def create_payment(self, amount: Decimal, order_id: int, 
                      user_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'url': f"https://www.paypal.com/checkoutnow?token=example_{order_id}",
            'provider': 'paypal',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        return payment_data.get('status') == 'COMPLETED'

class PaymeProvider(BasePaymentProvider):
    """Провайдер Payme"""
    
    def create_payment(self, amount: Decimal, order_id: int, 
                      user_data: Dict[str, Any]) -> Dict[str, Any]:
        amount_tiyin = int(amount * 100 * 12000)  # USD -> UZS -> tiyin
        
        return {
            'url': f"https://checkout.paycom.uz?m=example&a={amount_tiyin}&ac.order_id={order_id}",
            'provider': 'payme',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        return payment_data.get('state') == 2

class ClickProvider(BasePaymentProvider):
    """Провайдер Click"""
    
    def create_payment(self, amount: Decimal, order_id: int, 
                      user_data: Dict[str, Any]) -> Dict[str, Any]:
        amount_uzs = int(amount * 12000)  # USD -> UZS
        
        return {
            'url': f"https://my.click.uz/services/pay?service_id=example&amount={amount_uzs}&transaction_param={order_id}",
            'provider': 'click',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data: Dict[str, Any]) -> bool:
        return payment_data.get('error') == '0'