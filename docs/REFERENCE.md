# Stock Alert Monitor — Reference

Technical reference, architecture, and details for contributors. For setup and daily use, see [README](../readme.md).

> **IMPORTANT**: Any code change **must update this REFERENCE** (or README if it affects user-facing behavior) when it affects architecture, dependencies, behavior, or assumptions.

---

## Core Requirements

- Run on low-power hardware (Raspberry Pi)
- Configurable list of stocks
- Run once per day at 19:00, Monday–Friday only
- Alert when price is below a configurable % of the 200-day SMA
- Easy to extend with additional indicators
- Avoid duplicate/spam alerts
- Minimal operational overhead

---

## Design Decisions

### Execution Environment

- **Target**: Raspberry Pi (Linux) or Windows (testing only)
- **Language**: Python 3.11+
- **Scheduler**: `cron` (Linux) or Task Scheduler (Windows, testing only) — no long-running loops

Reasoning: reliable scheduling, very low power usage, simple recovery after reboot. Cross-platform Python code works on both Linux and Windows.

### Market Data Source

- **Primary**: Yahoo Finance via `yfinance`

Reasoning: free, sufficient for daily SMA strategies, no API keys. Designed so provider can be swapped later.

### Data Frequency

- Default: daily prices
- Scheduler may run multiple times per day, but indicators are evaluated against latest available data

### Persistence & State

- **Database**: SQLite

Used to store:

- Cached price history
- High-growth entry state per symbol (entry types already signalled, breakout levels)
- High-growth per-lot exit state (ATR_entry, fixed stops, trigger flags for partial exits, whether the initialization summary was already sent)
- High-growth per-lot negative-trend state (whether the 200 DMA / 200 WMA condition is currently active, to edge-trigger notifications)
- System status (last status notification date for weekly frequency tracking)

Reasoning: zero setup, reliable, prevents duplicate alerts after restarts.

### Notifications

- **Primary**: Telegram Bot API
- **Multiple recipients**: `TELEGRAM_CHAT_ID` accepts a comma-separated list of chat IDs; every alert, status message, and command listener authorization applies to all of them.
- **Status notifications**: Configurable frequency for operational status messages
  - `"every_run"`: Send status message on each scheduler execution (useful for initial verification)
  - `"weekly"`: Send status message once per week (minimizes noise)
  - `"disabled"`: No status messages (only sends actual alerts)
- **Alert mode** (`notifications.mode`): Configurable, controls which alert *types* fire — independent of `status_frequency`, which only governs the operational status message
  - `"all"`: Both entry alerts and exit alerts are sent (default)
  - `"only_exit"`: Entry alerts (watchlist) are suppressed entirely; exit alerts (per-lot) still fire
  - `"disabled"`: No entry or exit alerts are sent

### Alert Logic

There are **two independent alert systems**:

1. **High-growth entry alerts (per symbol, watchlist)**  
   - Uses [high-growth/entry.md](high-growth/entry.md) rules for each symbol in `stocks`  
   - Detects and alerts on:
     - **Entry Type 1 — ATH breakout** (new all-time high close)
     - **Entry Type 3 — High Tight Flag / volatility contraction**
     - **Entry Type 4 — First pullback to 200 DMA after breakout** (based on prior ATH breakout)  
   - Also **tracking**: reports when a watchlist stock is near or below 200 DMA or 200 WMA (drop from ATH, position vs 200 DMA/WMA).

2. **High-growth per-lot exit alerts (per bought position)**  
   - Uses [high-growth/exit.md](high-growth/exit.md) rules for each lot in `bought_positions`  
   - Each **lot** is one real-world buy with its own:
     - `EntryPrice`, fixed `ATR_entry`, original share size
     - Fixed stops (early failure, +50% lock, M1–M4 stops); partial-exit triggers are one-shot per stop  
   - **Initialization summary**: the first time a lot is processed (no prior stop state in SQLite), the system sends a single message listing all currently active stops for that lot. Later runs never repeat this summary — only changes are notified.
   - On each subsequent run the system:
     - Tells you when to **add a new stop** as price moves up  
     - Tells you when a **stop is breached** (symbol, lot id, rule name, shares to sell)
     - Sends a **negative trend notification** when weekly close newly falls below 200 DMA or 200 WMA — **edge-triggered**: it fires once when the condition transitions from false to true, is suppressed while the condition persists, and can fire again if the condition clears and re-triggers later
   - `main.py` never modifies `config.yaml`; the user adds/removes or updates lots and watchlist manually, either by hand-editing `config/config.yaml` or via the **Telegram command listener** below.

---

## Telegram Command Listener

A second, independent entry point — `src/telegram_command_listener.py` — lets the user manage `config/config.yaml` remotely via Telegram bot commands, instead of hand-editing the file.

### Execution Model

- Runs as its **own cron job**, separate from `main.py`, polling every 1-2 minutes (see `scripts/setup_cron.sh`).
- Each invocation: fetches new Telegram updates since the last stored offset (Telegram long-poll `getUpdates`, offset persisted in `system_status`), processes any commands, replies, and exits.
- No long-running process — consistent with the project's cron-only, run-once-and-exit execution model.

### Authorization

- Only messages from chat ID(s) configured in `.env` (`TELEGRAM_CHAT_ID`) are processed. `TELEGRAM_CHAT_ID` accepts either a single chat ID or a comma-separated list (`"111,222"`) to authorize multiple users. Commands from any other chat are logged and ignored (no reply sent), so the bot cannot be driven by unauthorized users even if its token/username is discovered. Replies are sent back to the sending chat, so each authorized user only sees their own command's ack/result.

### Commands

| Command | Effect |
|---|---|
| `/add_position id=<id> symbol=<symbol> entry_price=<price> shares=<qty>` | Appends a new lot to `bought_positions`. All 4 fields are required; missing or invalid fields fail with no file change. Fails if `id` already exists. |
| `/remove_position id=<id>` | Removes a lot from `bought_positions` by id. Fails if not found. |
| `/add_watch <SYMBOL>` | Appends a symbol to the `stocks` watchlist. Fails if already present. |
| `/remove_watch <SYMBOL>` | Removes a symbol from the `stocks` watchlist. Fails if not found. |
| `/status_frequency <every_run\|weekly\|disabled>` | Sets `notifications.status_frequency`. |
| `/mode <all\|only_exit\|disabled>` | Sets `notifications.mode`. |
| `/help` (or `/start`) | Lists all commands. |

### Behavior

- **Received acknowledgment**: as soon as an authorized command message arrives, the bot immediately replies `📩 Received: <text>` before processing it, so the user has confirmation the message reached the bot even if the config edit itself fails.
- **Result reply**: after processing, the bot replies with either a `✅` success message or a `❌` error message (e.g. missing fields, duplicate id, unknown value) — errors never partially modify the file.
- **Config edits are line-based, not a full YAML re-parse/re-dump** (`src/config_editor.py`): each command finds and edits only the specific line(s) it targets, preserving all comments and formatting elsewhere in `config.yaml` exactly as-is. A full YAML round-trip library was tried and rejected — it reformatted/misplaced entries near comment boundaries in this hand-maintained file.

---

## Project Structure

```
stock-alert-monitor/
│
├── README.md              # User-facing overview and setup
├── config/
│   └── config.yaml        # Stocks, bought positions, scheduling, notifications
│
├── docs/
│   ├── REFERENCE.md       # This file — architecture and reference
│   └── high-growth/       # Entry/exit rule specifications
│
├── src/
│   ├── main.py                    # Entry point (called by cron/scheduler)
│   ├── telegram_command_listener.py # Remote config edits via Telegram bot commands
│   ├── config_editor.py           # Line-based, comment-preserving config.yaml edits
│   ├── data_provider.py           # Market data access layer
│   ├── high_growth_entry_engine.py # High-growth entry rules (watchlist)
│   ├── high_growth_exit_engine.py # High-growth exit rules (per-lot)
│   ├── notifier/
│   │   ├── base.py        # Notification interface
│   │   └── telegram.py    # Telegram implementation
│   └── storage/
│       ├── db.py          # SQLite connection & migrations
│       └── models.py      # Tables and queries
│
├── scripts/
│   ├── setup_cron.sh              # Linux cron setup (main.py + telegram_command_listener.py)
│   ├── setup_task_scheduler.ps1   # Windows Task Scheduler (PowerShell)
│   └── setup_task_scheduler.bat   # Windows Task Scheduler (batch)
│
├── logs/
│   └── app.log           # Application logs
│
├── requirements.txt
└── .env                  # Secrets (not committed)
```

---

## Configuration Reference

All user-adjustable parameters live in `config/config.yaml`.

- **`stocks`**: Watchlist symbols for high-growth **entry** alerts and **tracking**.
- **`bought_positions`**: Per-lot high-growth positions; the user maintains this list manually:
  - `id` (any unique string), `symbol`, `entry_price`, `shares`
  - The system derives and stores `ATR_entry`, fixed stops, and partial-exit triggers in SQLite.
- **`notifications.status_frequency`**:
  - `"every_run"`: Status message every run (good for initial verification).
  - `"weekly"`: One status message per week.
  - `"disabled"`: No status messages; only alerts.
- **`notifications.mode`**: Which alert types are sent (independent of `status_frequency`).
  - `"all"` (default): Entry alerts and exit alerts both fire.
  - `"only_exit"`: Entry alerts are suppressed; exit alerts (stop additions, stop breaches, negative-trend transitions, initialization summary) still fire.
  - `"disabled"`: No entry or exit alerts are sent.

Status messages include: number of watchlist stocks and bought lots processed, and run timestamp.

---

## Extensibility

### Adding a New Notification Channel

1. Implement the notifier interface in `src/notifier/`
2. Add a configuration toggle in `config.yaml` and wire it in `main.py`
3. Update this REFERENCE and README if user-facing

---

## Operational Model

- Scheduler (cron on Linux, Task Scheduler on Windows) runs `main.py` at configured times (e.g. 19:00); the app runs analysis only on weekdays (Monday–Friday).
- Script runs once and exits.
- State is persisted only in SQLite (no long-running process).

---

## Non-Goals (Explicit)

- No real-time trading
- No order execution
- No high-frequency data
- No web UI (CLI + notifications only)

---

## Testing

Run the pipeline manually:

```bash
python src/main.py
```

Logs go to `logs/app.log` and (if configured) to Telegram.

### Automated tests

`tests/` covers `config_editor.py` and `telegram_command_listener.py` with no real Telegram API calls — HTTP is mocked (`unittest.mock`), and config edits run against a throwaway temp copy of `config/config.yaml`, never the real file:

```bash
python -m unittest discover -s tests
```
