"""Base notification interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class Notifier(ABC):
    """Abstract base class for all notifiers."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize notifier.
        
        Args:
            name: Notifier name (e.g., 'telegram')
            config: Configuration dictionary from config.yaml
        """
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', False)
    
    @abstractmethod
    def send(self, message: str) -> bool:
        """Send a notification message.
        
        Args:
            message: Message to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        pass
