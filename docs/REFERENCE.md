# Stock Alert Monitor — Reference

Technical reference, architecture, and details for contributors. For setup and daily use, see [README](../readme.md) and [SETUP](SETUP.md).

> **IMPORTANT**: Any code change **must update this REFERENCE** (or README if it affects user-facing behavior) when it affects architecture, dependencies, behavior, or assumptions.

---

## Core Requirements

- Run on low-power hardware (Raspberry Pi)
- Configurable list of stocks
- Configurable check frequency (times per day)
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
- High-growth per-lot exit state (ATR_entry, fixed stops, trigger flags for partial exits)
- System status (last status notification date for weekly frequency tracking)

Reasoning: zero setup, reliable, prevents duplicate alerts after restarts.

### Notifications

- **Primary**: Telegram Bot API
- **Status notifications**: Configurable frequency for operational status messages
  - `"every_run"`: Send status message on each scheduler execution (useful for initial verification)
  - `"weekly"`: Send status message once per week (minimizes noise)
  - `"disabled"`: No status messages (only sends actual alerts)

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
   - Once per day the system:
     - Tells you when to **add a new stop** as price moves up  
     - Tells you when a **stop or structural rule is breached** (symbol, lot id, rule name, shares to sell)  
   - The system **never modifies** `config.yaml`; the user adds/removes or updates lots and watchlist in `config/config.yaml` manually (e.g. after selling).

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
│   ├── SETUP.md           # Detailed setup (Telegram, cron, etc.)
│   └── high-growth/       # Entry/exit rule specifications
│
├── src/
│   ├── main.py                    # Entry point (called by cron/scheduler)
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
│   ├── setup_cron.sh              # Linux cron setup
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

Status messages include: number of watchlist stocks and bought lots processed, and run timestamp.

---

## Extensibility

### Adding a New Notification Channel

1. Implement the notifier interface in `src/notifier/`
2. Add a configuration toggle in `config.yaml` and wire it in `main.py`
3. Update this REFERENCE and README if user-facing

---

## Operational Model

- Scheduler (cron on Linux, Task Scheduler on Windows) runs `main.py` at configured times.
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
