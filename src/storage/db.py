"""SQLite database connection and migrations."""
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    """Manages SQLite database connection and schema."""
    
    def __init__(self, db_path: str = "data/stock_monitor.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_schema()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_schema(self):
        """Initialize database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Price history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                UNIQUE(symbol, date)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON price_history(symbol, date DESC)")

        # High-growth per-lot state table (exit rules from docs/high-growth/exit.md)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS high_growth_lot_state (
                lot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                shares_original INTEGER NOT NULL,
                shares_remaining INTEGER NOT NULL,
                atr_entry REAL,
                initial_stop_price REAL,
                stop1_price REAL,
                stop2_price REAL,
                stop3_price REAL,
                stop4_price REAL,
                stop5_price REAL,
                structural_exit_triggered INTEGER NOT NULL DEFAULT 0,
                early_failure_triggered INTEGER NOT NULL DEFAULT 0,
                stop1_defined INTEGER NOT NULL DEFAULT 0,
                stop1_triggered INTEGER NOT NULL DEFAULT 0,
                m1_reached INTEGER NOT NULL DEFAULT 0,
                m2_reached INTEGER NOT NULL DEFAULT 0,
                m3_reached INTEGER NOT NULL DEFAULT 0,
                m4_reached INTEGER NOT NULL DEFAULT 0,
                stop2_triggered INTEGER NOT NULL DEFAULT 0,
                stop3_triggered INTEGER NOT NULL DEFAULT 0,
                stop4_triggered INTEGER NOT NULL DEFAULT 0,
                stop5_triggered INTEGER NOT NULL DEFAULT 0,
                last_eval_date DATE
            )
        """)

        # High-growth entry state table (entry rules from docs/high-growth/entry.md)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS high_growth_entry_state (
                symbol TEXT PRIMARY KEY,
                last_ath_close REAL,
                last_ath_signal_date DATE,
                breakout_level REAL,
                breakout_date DATE,
                type3_signal_date DATE,
                type4_signal_date DATE
            )
        """)
        
        # System status table (for tracking status notifications)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_status (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_date DATE
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database schema initialized at {self.db_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
