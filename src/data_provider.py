"""Market data access layer using yfinance."""
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import yfinance as yf

logger = logging.getLogger(__name__)


class DataProvider:
    """Provides market data from Yahoo Finance."""
    
    def __init__(self, cache_days: int = 365, refresh_hours: int = 1):
        """Initialize data provider.
        
        Args:
            cache_days: Number of days of historical data to cache
            refresh_hours: Refresh data if older than this many hours
        """
        self.cache_days = cache_days
        self.refresh_hours = refresh_hours
    
    def fetch_stock_data(self, symbol: str, period: Optional[str] = None) -> Optional[yf.Ticker]:
        """Fetch stock data for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            period: Period to fetch (e.g., '1y', '2y'). Defaults to cache_days.
            
        Returns:
            yfinance Ticker object or None if fetch fails
        """
        try:
            ticker = yf.Ticker(symbol)
            if period is None:
                # Fetch enough data for cache_days
                period = f"{max(self.cache_days // 365, 1)}y"
            
            # Trigger data fetch by accessing history
            ticker.history(period=period)
            return ticker
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None
    
    def get_price_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest price data for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dict with date, open, high, low, close, volume or None
        """
        ticker = self.fetch_stock_data(symbol)
        if ticker is None:
            return None
        
        try:
            # Get latest available data
            hist = ticker.history(period="5d")
            if hist.empty:
                logger.warning(f"No data available for {symbol}")
                return None
            
            latest = hist.iloc[-1]
            latest_date = hist.index[-1].date()
            
            return {
                'date': latest_date,
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'close': float(latest['Close']),
                'volume': int(latest['Volume'])
            }
        except Exception as e:
            logger.error(f"Error extracting price data for {symbol}: {e}")
            return None
    
    def get_historical_prices(self, symbol: str, days: int = 200) -> List[Dict[str, Any]]:
        """Get historical price data for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days to retrieve
            
        Returns:
            List of price dictionaries, ordered by date (oldest first)
        """
        ticker = self.fetch_stock_data(symbol)
        if ticker is None:
            return []
        
        try:
            # Fetch enough history
            period_days = max(days, 365)  # Fetch at least 1 year
            hist = ticker.history(period=f"{max(period_days // 365, 1)}y")
            
            if hist.empty:
                logger.warning(f"No historical data available for {symbol}")
                return []
            
            # Convert to list of dicts
            result = []
            for idx, row in hist.iterrows():
                result.append({
                    'date': idx.date(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            
            # Return last N days, oldest first
            return result[-days:] if len(result) > days else result
        except Exception as e:
            logger.error(f"Error extracting historical data for {symbol}: {e}")
            return []
