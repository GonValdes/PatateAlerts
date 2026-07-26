"""Telegram command listener.

Polls for incoming Telegram bot messages and mutates config/config.yaml
accordingly (bought_positions, the stocks watchlist, and notification
settings). Meant to run as its own frequent cron job (e.g. every 1-2
minutes), separate from main.py's once-daily analysis run: each invocation
fetches new updates since the last stored offset, processes any commands
from the authorized chat, replies, and exits.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from storage.db import Database
import config_editor as ce

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
OFFSET_KEY = "telegram_last_update_id"

HELP_TEXT = (
    "🤖 Available commands:\n\n"
    "/add_position id=<id> symbol=<symbol> entry_price=<price> shares=<qty>\n"
    "  Add a new bought-position lot. All 4 fields are required.\n\n"
    "/remove_position id=<id>\n"
    "  Remove a bought-position lot by id.\n\n"
    "/add_watch <SYMBOL>\n"
    "  Add a symbol to the high-growth watchlist.\n\n"
    "/remove_watch <SYMBOL>\n"
    "  Remove a symbol from the high-growth watchlist.\n\n"
    f"/status_frequency <{'|'.join(ce.VALID_STATUS_FREQUENCIES)}>\n"
    "  Change how often the operational status message is sent.\n\n"
    f"/mode <{'|'.join(ce.VALID_ALERT_MODES)}>\n"
    "  Change which alerts fire: all, exit-only, or none.\n\n"
    "/help\n"
    "  Show this message."
)


def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "telegram_commands.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _get_offset(db: Database) -> int:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_status WHERE key = ?", (OFFSET_KEY,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return 0
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return 0


def _set_offset(db: Database, offset: int) -> None:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO system_status (key, value, updated_date) VALUES (?, ?, date('now'))",
        (OFFSET_KEY, str(offset)),
    )
    conn.commit()
    conn.close()


def _fetch_updates(bot_token: str, offset: int) -> List[Dict[str, Any]]:
    url = TELEGRAM_API.format(token=bot_token, method="getUpdates")
    response = requests.get(url, params={"offset": offset, "timeout": 0}, timeout=15)
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        logger.error("getUpdates failed: %s", result.get("description"))
        return []
    return result.get("result", [])


def _send(bot_token: str, chat_id: str, text: str) -> None:
    url = TELEGRAM_API.format(token=bot_token, method="sendMessage")
    try:
        response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to send Telegram reply: %s", exc)


def _parse_kwargs(args: List[str], required: tuple) -> Dict[str, str]:
    """Parse key=value tokens. Raises ValueError listing unknown/missing keys."""
    parsed: Dict[str, str] = {}
    unknown = []
    for token in args:
        if "=" not in token:
            unknown.append(token)
            continue
        key, _, value = token.partition("=")
        key = key.strip().lower()
        if key not in required:
            unknown.append(token)
            continue
        parsed[key] = value.strip()

    if unknown:
        raise ValueError(f"Unrecognized argument(s): {', '.join(unknown)}")

    missing = [key for key in required if not parsed.get(key)]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    return parsed


def _handle_add_position(args: List[str]) -> str:
    fields = _parse_kwargs(args, ("id", "symbol", "entry_price", "shares"))

    try:
        entry_price = float(fields["entry_price"])
    except ValueError:
        raise ValueError(f"entry_price must be a number, got '{fields['entry_price']}'")

    try:
        shares = int(fields["shares"])
    except ValueError:
        raise ValueError(f"shares must be an integer, got '{fields['shares']}'")

    ce.add_bought_position(fields["id"], fields["symbol"], entry_price, shares)
    return f"✅ Added position {fields['id']} ({fields['symbol']}) @ {entry_price} x{shares}"


def _handle_remove_position(args: List[str]) -> str:
    fields = _parse_kwargs(args, ("id",))
    ce.remove_bought_position(fields["id"])
    return f"✅ Removed position {fields['id']}"


def _handle_add_watch(args: List[str]) -> str:
    if len(args) != 1:
        raise ValueError("Usage: /add_watch <SYMBOL>")
    symbol = args[0].strip()
    ce.add_watch_symbol(symbol)
    return f"✅ Added {symbol} to the watchlist"


def _handle_remove_watch(args: List[str]) -> str:
    if len(args) != 1:
        raise ValueError("Usage: /remove_watch <SYMBOL>")
    symbol = args[0].strip()
    ce.remove_watch_symbol(symbol)
    return f"✅ Removed {symbol} from the watchlist"


def _handle_status_frequency(args: List[str]) -> str:
    if len(args) != 1:
        raise ValueError(f"Usage: /status_frequency <{'|'.join(ce.VALID_STATUS_FREQUENCIES)}>")
    value = args[0].strip().lower()
    ce.set_status_frequency(value)
    return f'✅ status_frequency set to "{value}"'


def _handle_mode(args: List[str]) -> str:
    if len(args) != 1:
        raise ValueError(f"Usage: /mode <{'|'.join(ce.VALID_ALERT_MODES)}>")
    value = args[0].strip().lower()
    ce.set_alert_mode(value)
    return f'✅ Alert mode set to "{value}"'


def _handle_help(args: List[str]) -> str:
    return HELP_TEXT


COMMANDS = {
    "add_position": _handle_add_position,
    "remove_position": _handle_remove_position,
    "add_watch": _handle_add_watch,
    "remove_watch": _handle_remove_watch,
    "status_frequency": _handle_status_frequency,
    "mode": _handle_mode,
    "help": _handle_help,
    "start": _handle_help,
}


def _process_message(bot_token: str, chat_id: str, text: str) -> None:
    text = (text or "").strip()
    if not text.startswith("/"):
        return

    parts = text.split()
    command = parts[0][1:].split("@")[0].lower()  # strip Telegram's /cmd@BotName form
    args = parts[1:]

    # Immediate feedback that the message arrived, before it's processed.
    _send(bot_token, chat_id, f"📩 Received: {text}")

    handler = COMMANDS.get(command)
    if handler is None:
        _send(bot_token, chat_id, f"❓ Unknown command '{command}'. Send /help for the list of commands.")
        return

    try:
        reply = handler(args)
    except ValueError as exc:
        reply = f"❌ {exc}"
    except Exception as exc:
        logger.error("Error handling command '%s': %s", command, exc, exc_info=True)
        reply = f"❌ Unexpected error: {exc}"

    _send(bot_token, chat_id, reply)


def main():
    setup_logging()
    logger.info("Checking for Telegram commands")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    authorized_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not authorized_chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured; skipping command check")
        return

    db = Database()
    offset = _get_offset(db)

    try:
        updates = _fetch_updates(bot_token, offset)
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to fetch Telegram updates: %s", exc)
        return

    for update in updates:
        update_id = update["update_id"]
        message = update.get("message") or update.get("edited_message")

        if message:
            sender_chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "")

            if sender_chat_id != str(authorized_chat_id):
                logger.warning("Ignoring command from unauthorized chat_id %s", sender_chat_id)
            else:
                try:
                    _process_message(bot_token, authorized_chat_id, text)
                except Exception as exc:
                    logger.error("Error processing message: %s", exc, exc_info=True)

        # Advance the offset regardless of outcome so a bad update can't block the queue forever.
        _set_offset(db, update_id + 1)

    if updates:
        logger.info("Processed %d Telegram update(s)", len(updates))


if __name__ == "__main__":
    main()
