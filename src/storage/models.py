"""Database models and query functions."""
import sqlite3
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from .db import Database


class PriceHistory:
    """Price history data model."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def insert_or_update(self, symbol: str, date: date, open: float, high: float, 
                        low: float, close: float, volume: int):
        """Insert or update price data for a symbol and date."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO price_history 
            (symbol, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, date, open, high, low, close, volume))
        conn.commit()
        conn.close()
    
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the latest price data for a symbol.
        
        Returns:
            Dict with date, open, high, low, close, volume or None
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, open, high, low, close, volume
            FROM price_history
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
        """, (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'date': row['date'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }
        return None
    
    def get_historical_prices(self, symbol: str, days: int = 200) -> List[Dict[str, Any]]:
        """Get historical price data for a symbol.
        
        Args:
            symbol: Stock symbol
            days: Number of days to retrieve
            
        Returns:
            List of price dictionaries, ordered by date (oldest first)
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, open, high, low, close, volume
            FROM price_history
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """, (symbol, days))
        rows = cursor.fetchall()
        conn.close()
        
        # Return in chronological order (oldest first)
        result = []
        for row in reversed(rows):
            result.append({
                'date': row['date'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            })
        return result


class HighGrowthLotState:
    """Per-lot state for high-growth exit rules.

    Tracks ATR_entry, fixed stops, milestone activation, and one-time triggers
    for each manually-defined lot in config.bought_positions.
    """

    def __init__(self, db: Database):
        self.db = db

    def get_state(self, lot_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a given lot_id."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM high_growth_lot_state
            WHERE lot_id = ?
            """,
            (lot_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return dict(row)

    def upsert_state(self, state: Dict[str, Any]) -> None:
        """Insert or replace lot state row."""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO high_growth_lot_state (
                lot_id,
                symbol,
                entry_price,
                shares_original,
                shares_remaining,
                atr_entry,
                initial_stop_price,
                stop1_price,
                stop2_price,
                stop3_price,
                stop4_price,
                stop5_price,
                structural_exit_triggered,
                early_failure_triggered,
                stop1_defined,
                stop1_triggered,
                m1_reached,
                m2_reached,
                m3_reached,
                m4_reached,
                stop2_triggered,
                stop3_triggered,
                stop4_triggered,
                stop5_triggered,
                trend_below_dma_active,
                trend_below_wma_active,
                last_eval_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state["lot_id"],
                state["symbol"],
                state["entry_price"],
                state["shares_original"],
                state["shares_original"],  # shares_remaining column kept for backward compatibility, but not used
                state.get("atr_entry"),
                state.get("initial_stop_price"),
                state.get("stop1_price"),
                state.get("stop2_price"),
                state.get("stop3_price"),
                state.get("stop4_price"),
                state.get("stop5_price"),
                1 if state.get("structural_exit_triggered") else 0,
                1 if state.get("early_failure_triggered") else 0,
                1 if state.get("stop1_defined") else 0,
                1 if state.get("stop1_triggered") else 0,
                1 if state.get("m1_reached") else 0,
                1 if state.get("m2_reached") else 0,
                1 if state.get("m3_reached") else 0,
                1 if state.get("m4_reached") else 0,
                1 if state.get("stop2_triggered") else 0,
                1 if state.get("stop3_triggered") else 0,
                1 if state.get("stop4_triggered") else 0,
                1 if state.get("stop5_triggered") else 0,
                1 if state.get("trend_below_dma_active") else 0,
                1 if state.get("trend_below_wma_active") else 0,
                state.get("last_eval_date"),
            ),
        )

        conn.commit()
        conn.close()

    def create_default_state(
        self, lot_id: str, symbol: str, entry_price: float, shares: int
    ) -> Dict[str, Any]:
        """Return an in-memory default state for a new lot (not yet persisted)."""
        return {
            "lot_id": lot_id,
            "symbol": symbol,
            "entry_price": entry_price,
            "shares_original": shares,
            "atr_entry": None,
            "initial_stop_price": None,
            "stop1_price": None,
            "stop2_price": None,
            "stop3_price": None,
            "stop4_price": None,
            "stop5_price": None,
            "structural_exit_triggered": False,
            "early_failure_triggered": False,
            "stop1_defined": False,
            "stop1_triggered": False,
            "m1_reached": False,
            "m2_reached": False,
            "m3_reached": False,
            "m4_reached": False,
            "stop2_triggered": False,
            "stop3_triggered": False,
            "stop4_triggered": False,
            "stop5_triggered": False,
            "trend_below_dma_active": False,
            "trend_below_wma_active": False,
            "last_eval_date": None,
        }


class HighGrowthEntryState:
    """Per-symbol state for high-growth entry rules.

    Tracks ATH breakout levels and one-shot entry signals per type.
    """

    def __init__(self, db: Database):
        self.db = db

    def get_state(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current state for a given symbol."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM high_growth_entry_state
            WHERE symbol = ?
            """,
            (symbol,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return dict(row)

    def upsert_state(self, state: Dict[str, Any]) -> None:
        """Insert or replace entry state row."""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO high_growth_entry_state (
                symbol,
                last_ath_close,
                last_ath_signal_date,
                breakout_level,
                breakout_date,
                type3_signal_date,
                type4_signal_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state["symbol"],
                state.get("last_ath_close"),
                state.get("last_ath_signal_date"),
                state.get("breakout_level"),
                state.get("breakout_date"),
                state.get("type3_signal_date"),
                state.get("type4_signal_date"),
            ),
        )

        conn.commit()
        conn.close()

    def create_default_state(self, symbol: str) -> Dict[str, Any]:
        """Return an in-memory default state for a symbol (not yet persisted)."""
        return {
            "symbol": symbol,
            "last_ath_close": None,
            "last_ath_signal_date": None,
            "breakout_level": None,
            "breakout_date": None,
            "type3_signal_date": None,
            "type4_signal_date": None,
        }
