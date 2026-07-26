"""Programmatic edits to config/config.yaml.

Line-based edits (not a full YAML round-trip) so comments and formatting in
the hand-maintained file are preserved exactly. Used by the Telegram command
listener to mutate the watchlist, bought positions, and notification
settings without a human hand-editing the file. All functions raise
ValueError on invalid input (missing/duplicate/not-found) and leave the file
untouched in that case.
"""
import logging
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"

VALID_STATUS_FREQUENCIES = ("every_run", "weekly", "disabled")
VALID_ALERT_MODES = ("all", "only_exit", "disabled")


def _read(config_path: Path) -> str:
    return config_path.read_text(encoding="utf-8")


def _write(config_path: Path, text: str) -> None:
    config_path.write_text(text, encoding="utf-8")


def _find_block(lines: List[str], header: str) -> Tuple[int, int]:
    """Find the [start, end) line-index range of the block under `header:`.

    `start` is the index right after the header line. `end` is the index of
    the first subsequent line that is non-blank and not indented (the next
    top-level section), or len(lines).
    """
    header_line = f"{header}:"
    start = None
    for i, line in enumerate(lines):
        if line.rstrip("\n") == header_line:
            start = i + 1
            break
    if start is None:
        raise ValueError(f"Could not find '{header}:' section in config.yaml")

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].strip() == "":
            continue
        if not lines[i].startswith(" "):
            end = i
            break
    return start, end


# ---- stocks watchlist -----------------------------------------------------

def _stock_symbol(line: str) -> str:
    """Extract the bare symbol from a stocks list line, ignoring comments/commented-out lines."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return ""
    if stripped.startswith("-"):
        stripped = stripped[1:].strip()
    return stripped.split("#", 1)[0].strip()


def add_watch_symbol(symbol: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Append a symbol to the stocks watchlist. Raises ValueError if already present."""
    lines = _read(config_path).splitlines(keepends=True)
    start, end = _find_block(lines, "stocks")

    if any(_stock_symbol(line) == symbol for line in lines[start:end]):
        raise ValueError(f"'{symbol}' is already in the watchlist")

    insert_at = end
    while insert_at > start and lines[insert_at - 1].strip() == "":
        insert_at -= 1

    lines.insert(insert_at, f"  - {symbol}\n")
    _write(config_path, "".join(lines))
    logger.info("Added watchlist symbol %s", symbol)


def remove_watch_symbol(symbol: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Remove a symbol from the stocks watchlist. Raises ValueError if not found."""
    lines = _read(config_path).splitlines(keepends=True)
    start, end = _find_block(lines, "stocks")

    for i in range(start, end):
        if _stock_symbol(lines[i]) == symbol:
            del lines[i]
            _write(config_path, "".join(lines))
            logger.info("Removed watchlist symbol %s", symbol)
            return

    raise ValueError(f"'{symbol}' not found in the watchlist")


# ---- bought_positions -------------------------------------------------------

def _lot_entries(lines: List[str], start: int, end: int) -> List[Tuple[int, int, str]]:
    """Split the bought_positions block into (entry_start, entry_end, lot_id) tuples."""
    entries = []
    i = start
    while i < end:
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        m = re.match(r'^\s*-\s*id:\s*"?([^"\s]+)"?\s*(#.*)?$', line)
        if not m:
            i += 1
            continue
        entry_start = i
        j = i + 1
        while j < end and lines[j].startswith("    "):
            j += 1
        entries.append((entry_start, j, m.group(1)))
        i = j
    return entries


def add_bought_position(
    lot_id: str,
    symbol: str,
    entry_price: float,
    shares: int,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> None:
    """Append a new lot to bought_positions. Raises ValueError if the id already exists."""
    lines = _read(config_path).splitlines(keepends=True)
    start, end = _find_block(lines, "bought_positions")
    entries = _lot_entries(lines, start, end)

    if any(existing_id == lot_id for _, _, existing_id in entries):
        raise ValueError(f"Position id '{lot_id}' already exists")

    new_entry = (
        f'  - id: "{lot_id}"\n'
        f"    symbol: {symbol}\n"
        f"    entry_price: {entry_price}\n"
        f"    shares: {int(shares)}\n"
    )

    insert_at = entries[-1][1] if entries else start
    lines.insert(insert_at, new_entry)
    _write(config_path, "".join(lines))
    logger.info("Added bought position %s (%s)", lot_id, symbol)


def remove_bought_position(lot_id: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Remove a lot from bought_positions by id. Raises ValueError if not found."""
    lines = _read(config_path).splitlines(keepends=True)
    start, end = _find_block(lines, "bought_positions")
    entries = _lot_entries(lines, start, end)

    match = next(((s, e) for s, e, existing_id in entries if existing_id == lot_id), None)
    if match is None:
        raise ValueError(f"Position id '{lot_id}' not found")

    entry_start, entry_end = match
    del lines[entry_start:entry_end]
    _write(config_path, "".join(lines))
    logger.info("Removed bought position %s", lot_id)


# ---- notification settings ---------------------------------------------------

def _set_scalar_field(field: str, value: str, config_path: Path) -> None:
    text = _read(config_path)
    pattern = re.compile(rf'^(\s*{re.escape(field)}:\s*)"[^"]*"(\s*(#.*)?)$', re.MULTILINE)
    new_text, count = pattern.subn(rf'\1"{value}"\2', text)
    if count == 0:
        raise ValueError(f"Could not find '{field}:' in the notifications section")
    _write(config_path, new_text)


def set_status_frequency(value: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Set notifications.status_frequency. Raises ValueError if value is invalid."""
    if value not in VALID_STATUS_FREQUENCIES:
        raise ValueError(
            f"Invalid status_frequency '{value}'; must be one of {', '.join(VALID_STATUS_FREQUENCIES)}"
        )
    _set_scalar_field("status_frequency", value, config_path)
    logger.info("Set status_frequency to %s", value)


def set_alert_mode(value: str, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Set notifications.mode. Raises ValueError if value is invalid."""
    if value not in VALID_ALERT_MODES:
        raise ValueError(f"Invalid mode '{value}'; must be one of {', '.join(VALID_ALERT_MODES)}")
    _set_scalar_field("mode", value, config_path)
    logger.info("Set alert mode to %s", value)
