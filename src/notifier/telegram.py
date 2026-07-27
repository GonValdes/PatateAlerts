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
        self.chat_ids = [cid.strip() for cid in (os.getenv('TELEGRAM_CHAT_ID') or '').split(',') if cid.strip()]

        if self.enabled and (not self.bot_token or not self.chat_ids):
            logger.warning("Telegram notifier enabled but missing bot_token or chat_id in .env")
            self.enabled = False

    def send(self, message: str) -> bool:
        """Send message via Telegram bot to every configured chat ID.

        Args:
            message: Message to send

        Returns:
            True if sent successfully to at least one chat, False otherwise
        """
        if not self.enabled:
            return False

        if not self.bot_token or not self.chat_ids:
            logger.error("Telegram credentials not configured")
            return False

        any_success = False
        for chat_id in self.chat_ids:
            if self._send_to_chat(chat_id, message):
                any_success = True
        return any_success

    def _send_to_chat(self, chat_id: str, message: str) -> bool:
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message
            }

            logger.debug(f"Sending Telegram message to chat_id {chat_id}")
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                logger.info(f"Telegram notification sent successfully to chat_id {chat_id}")
                return True
            else:
                logger.error(f"Telegram API error for chat_id {chat_id}: {result.get('description', 'Unknown error')}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram notification to chat_id {chat_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Telegram API response: {error_detail}")
                except:
                    logger.error(f"Telegram API response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification to chat_id {chat_id}: {e}", exc_info=True)
            return False
