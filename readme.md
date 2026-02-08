# Stock Alert Monitor

## Purpose
Low-power, always-on Python system to monitor a list of stocks and send alerts when price-based technical conditions are met.

This repository **defines the base architecture** of the project.

> **IMPORTANT RULE**: Any future code change **must update this README** if it affects architecture, dependencies, behavior, or assumptions.

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
- **Scheduler**: `cron` (Linux) or Task Scheduler (Windows, testing only) - no long-running loops

Reasoning: reliable scheduling, very low power usage, simple recovery after reboot. Cross-platform Python code works on both Linux and Windows.

---

### Market Data Source
- **Primary**: Yahoo Finance via `yfinance`

Reasoning: free, sufficient for daily SMA strategies, no API keys. Designed so provider can be swapped later.

---

### Data Frequency
- Default: daily prices
- Scheduler may run multiple times per day, but indicators are evaluated against latest available data

---

### Persistence & State
- **Database**: SQLite

Used to store:
- Cached price history
- High-growth entry state per symbol (entry types already signalled, breakout levels)
- High-growth per-lot exit state (ATR_entry, fixed stops, trigger flags, remaining shares)
- System status (last status notification date for weekly frequency tracking)

Reasoning: zero setup, reliable, prevents duplicate alerts after restarts.

---

### Notifications
- **Primary**: Telegram Bot API
- **Status notifications**: Configurable frequency for operational status messages
  - `"every_run"`: Send status message on each scheduler execution (useful for initial verification)
  - `"weekly"`: Send status message once per week (minimizes noise)
  - `"disabled"`: No status messages (only sends actual alerts)

---

### Alert Logic

There are **two independent alert systems**:

1. **High-growth entry alerts (per symbol, watchlist)**  
   - Uses `docs/high-growth/entry.md` rules for each symbol in `stocks`  
   - Enforces global entry condition: **Daily Close ≥ 200 DMA**  
   - Detects and alerts on:
     - **Entry Type 1 — ATH breakout** (new all-time high close)
     - **Entry Type 3 — High Tight Flag / volatility contraction** (approximate implementation)
     - **Entry Type 4 — First pullback to 200 DMA after breakout** (based on prior ATH breakout)  
   - Each entry type is signalled at most **once per symbol** (no duplicate spam).

2. **High-growth per-lot exit alerts (per bought position)**  
   - Uses `docs/high-growth/exit.md` rules for each lot in `bought_positions`  
   - Each **lot** is one real-world buy with its own:
     - `EntryPrice`, fixed `ATR_entry`, original share size
     - Fixed stops (early failure, +50% lock, M1–M4 stops), each single-use  
   - Once per day (at the configured evaluation time) the system:
     - Tells you when to **add a new stop** as price moves up  
     - Tells you when a **stop or structural rule is breached**, including:
       - Stock symbol and lot id
       - Which rule/stop triggered
       - **Exact number of shares to sell** for that lot  
   - The system **never modifies** the `bought_positions` list; you add/remove lots manually.

---

## Project Structure

```
stock-alert-monitor/
│
├── README.md              # Architecture & decisions (must stay updated)
├── config/
│   └── config.yaml        # Stocks, thresholds, scheduling parameters
│
├── src/
│   ├── main.py                    # Entry point (called by cron)
│   ├── data_provider.py           # Market data access layer
│   ├── high_growth_entry_engine.py# High-growth entry rules (watchlist)
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
│   ├── setup_task_scheduler.ps1   # Windows Task Scheduler setup (PowerShell)
│   └── setup_task_scheduler.bat   # Windows Task Scheduler setup (batch)
│
├── logs/
│   └── app.log            # Rotated logs
│
├── requirements.txt
└── .env                   # Secrets (not committed)
```

---

## Configuration
- All user-adjustable parameters live in `config/config.yaml`
- No hard-coded stock lists or thresholds in code
- `stocks`: watchlist symbols for high-growth **entry** alerts
- `bought_positions`: **per-lot** high-growth positions you maintain manually:
  - `id` (any unique string you choose)
  - `symbol`, `entry_price`, `shares`
  - The system derives and stores `ATR_entry`, fixed stops, and triggers in SQLite.
- `notifications.status_frequency`: Controls how often status notifications are sent:
  - **`"every_run"`** (default for initial setup): Sends a status message every time the scheduler runs. Useful for verifying the system is working correctly during the first weeks of operation.
  - **`"weekly"`**: Sends one status message per week (checks if 7+ days have passed since last status). Use this after initial verification to minimize noise while still confirming the system is operational.
  - **`"disabled"`**: No status messages are sent. Only actual alerts (entry signals, exit triggers) will be sent.
  
  Status messages include:
  - Number of watchlist stocks processed
  - Number of bought lots processed
  - Timestamp of the run

---

## Extensibility Rules

### Adding a New Notification Channel
1. Implement notifier interface in `src/notifier/`
2. Add configuration toggle
3. Update this README

---

## Operational Model
- Scheduler (cron on Linux, Task Scheduler on Windows) triggers `main.py`
- Script exits after completion
- Stateless execution except for SQLite persistence

---

## Non-Goals (Explicit)
- No real-time trading
- No order execution
- No high-frequency data
- No web UI (CLI + notifications only)

---

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Copy `env.example` to `.env`
   - Add your Telegram bot token and chat ID (if using Telegram notifications)

3. **Configure stocks:**
   - Edit `config/config.yaml` to add your stock symbols and adjust thresholds

### Scheduling

#### Linux (cron)
Run the setup script:
```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```
Or manually add to crontab:
```bash
0 9,12,15,18 * * * cd /path/to/project && python3 src/main.py >> logs/cron.log 2>&1
```

#### Windows (Task Scheduler)
Run PowerShell as Administrator:
```powershell
.\scripts\setup_task_scheduler.ps1
```
Or use the batch script:
```cmd
scripts\setup_task_scheduler.bat
```

### Testing
Run manually to test:
```bash
python src/main.py
```

---

## Next Planned Step
- Define configuration file schema
- Define SQLite schema
- Implement indicator base interface

