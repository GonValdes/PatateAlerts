"""Main entry point for stock alert monitor."""
import sys
import logging
import yaml
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from storage.db import Database
from data_provider import DataProvider
from notifier.telegram import TelegramNotifier
from high_growth_exit_engine import HighGrowthExitEngine
from high_growth_entry_engine import HighGrowthEntryEngine
from datetime import date, timedelta


def setup_logging():
    """Configure logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "app.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    return config


def main():
    """Main execution function."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting stock alert monitor")

    try:
        # Load configuration
        config = load_config()

        # Initialize database
        db = Database()

        # Initialize data provider
        data_config = config.get("data", {})
        data_provider = DataProvider(
            cache_days=data_config.get("cache_days", 365),
            refresh_hours=data_config.get("refresh_hours", 1),
        )

        # Initialize notifiers
        notifiers = []
        notifications_config = config.get("notifications", {})

        if notifications_config.get("telegram", {}).get("enabled", False):
            telegram_notifier = TelegramNotifier(notifications_config["telegram"])
            notifiers.append(telegram_notifier)
            
            # Send status notification based on configured frequency
            status_frequency = notifications_config.get("status_frequency", "disabled")
            if telegram_notifier.enabled and status_frequency != "disabled":
                should_send_status = _should_send_status_notification(db, status_frequency)
                if should_send_status:
                    status_msg = (
                        "📊 Stock Alert Monitor Status\n\n"
                        f"✅ Processing {len(config.get('stocks', []))} watchlist stocks\n"
                        f"✅ Processing {len(config.get('bought_positions', []))} bought lots\n"
                        f"🕐 Run completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    logger.info("Sending status notification...")
                    if telegram_notifier.send(status_msg):
                        logger.info("Status notification sent successfully")
                        _update_last_status_date(db, date.today())
                    else:
                        logger.warning("Status notification failed - check credentials in .env")
                else:
                    logger.debug("Skipping status notification (frequency: %s)", status_frequency)

        # Initialize engines
        high_growth_exit_engine = HighGrowthExitEngine(db, data_provider, notifiers)
        high_growth_entry_engine = HighGrowthEntryEngine(db, data_provider, notifiers)

        # Process watchlist stocks for high-growth entries
        stocks = config.get("stocks", [])
        if stocks:
            logger.info(f"Processing {len(stocks)} watchlist stocks for high-growth entries")
            for symbol in stocks:
                try:
                    high_growth_entry_engine.process_symbol(symbol)
                except Exception as e:
                    logger.error(f"Error processing high-growth entries for {symbol}: {e}", exc_info=True)
        else:
            if not stocks:
                logger.info("No stocks configured in watchlist; skipping indicator alerts")

        # Process high-growth bought lots (per-lot exit logic)
        bought_positions = config.get("bought_positions", [])
        if bought_positions:
            logger.info(f"Processing {len(bought_positions)} bought lots for high-growth exits")
            for lot in bought_positions:
                try:
                    high_growth_exit_engine.process_lot(lot)
                except Exception as e:
                    logger.error(
                        "Error processing lot %s (%s): %s",
                        lot.get("id"),
                        lot.get("symbol"),
                        e,
                        exc_info=True,
                    )
        else:
            logger.info("No bought_positions configured; skipping high-growth exit logic")

        logger.info("Stock alert monitor completed successfully")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def _should_send_status_notification(db: Database, frequency: str) -> bool:
    """Check if status notification should be sent based on frequency setting.
    
    Args:
        db: Database instance
        frequency: "every_run", "weekly", or "disabled"
        
    Returns:
        True if notification should be sent, False otherwise
    """
    if frequency == "disabled":
        return False
    
    if frequency == "every_run":
        return True
    
    if frequency == "weekly":
        # Check last status date
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM system_status WHERE key = ?",
            ("last_status_date",)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            # Never sent before, send now
            return True
        
        try:
            last_date = date.fromisoformat(row["value"])
            days_since = (date.today() - last_date).days
            return days_since >= 7
        except (ValueError, TypeError):
            # Invalid date, send now
            return True
    
    # Unknown frequency, default to False
    logger.warning("Unknown status_frequency: %s, defaulting to disabled", frequency)
    return False


def _update_last_status_date(db: Database, status_date: date) -> None:
    """Update the last status notification date in database."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO system_status (key, value, updated_date) VALUES (?, ?, ?)",
        ("last_status_date", status_date.isoformat(), status_date)
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
