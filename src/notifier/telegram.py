"""Telegram bot notifier implementation."""
import logging
import os
import requests
from typing import Dict, Any
from .base import Notifier

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    """Telegram bot notification implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Telegram notifier.
        
        Args:
            config: Configuration dict (enabled flag)
        """
        super().__init__('telegram', config)
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if self.enabled and (not self.bot_token or not self.chat_id):
            logger.warning("Telegram notifier enabled but missing bot_token or chat_id in .env")
            self.enabled = False
    
    def send(self, message: str) -> bool:
        """Send message via Telegram bot.
        
        Args:
            message: Message to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram credentials not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message
            }
            
            logger.debug(f"Sending Telegram message to chat_id {self.chat_id}")
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Telegram API response: {error_detail}")
                except:
                    logger.error(f"Telegram API response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification: {e}", exc_info=True)
            return False
