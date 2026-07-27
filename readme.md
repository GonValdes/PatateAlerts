# Stock Alert Monitor

Python app that monitors a list of stocks and sends alerts when price-based conditions are met (high-growth entry signals and per-lot exit rules). Designed to run on a schedule (e.g. Raspberry Pi or Windows) with minimal setup. Runs on **Linux** and **Windows**; use a virtual environment so cron or Task Scheduler use the same Python and dependencies.

---

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

---

## Setup

### 1. Virtual environment

Create and activate a venv in the project directory:

```bash
python -m venv .venv
```

**Activate:**

| Platform | Command |
|----------|---------|
| Linux / macOS | `source .venv/bin/activate` |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (Command Prompt) | `.venv\Scripts\activate.bat` |

When active, the prompt usually shows `(.venv)`.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

- Copy `env.example` to `.env`
- If you use Telegram notifications, add your bot token and chat ID (see [Telegram setup](#telegram-notifications) below).

### 4. Configure stocks

Edit **`config/config.yaml`**:

- **Stocks to monitor** — Under `stocks:`, list symbols for entry and tracking alerts.
- **Bought positions** — Under `bought_positions:`, add each lot you own: `id`, `symbol`, `entry_price`, `shares`. The app evaluates exit rules and notifies when stops are hit.
- **Settings** — Adjust scheduling, notifications, and data cache as needed.

**You are responsible for keeping `config.yaml` up to date.** When you buy or sell in real life, add, remove, or update entries in `config/config.yaml` (e.g. remove a lot after you’ve sold). `main.py` never changes your config on its own — but you can also make these edits remotely via Telegram commands instead of hand-editing the file (see [Telegram commands](#telegram-commands) below).

---

## Telegram notifications

To receive alerts via Telegram:

**1. Create a bot** — In Telegram, open `@BotFather`, send `/newbot`, follow the prompts. Save the **bot token** (e.g. `123456789:ABCdef...`).

**2. Get your Chat ID** — Send a message to your bot, then open in a browser (use your token):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
   Find `"chat":{"id":123456789}` — the number is your **chat ID**.

**3. Configure `.env`** — Set:
   ```env
   TELEGRAM_BOT_TOKEN="your_bot_token_here"
   TELEGRAM_CHAT_ID="your_chat_id_here"
   ```
   Use quotes; chat ID is numeric only (no `@`).

   **Multiple users** — To send alerts to more than one person, list their chat IDs comma-separated: `TELEGRAM_CHAT_ID="111111111,222222222"`. Everyone on the list receives every alert and status message, and everyone on the list can send [Telegram commands](#telegram-commands) to the bot (each gets their own ack/result replies).

**4. Test** — With the venv activated, run `python src/main.py`. You should get a message in Telegram. If not: check logs, verify token and numeric chat ID, and that you’ve sent at least one message to the bot.

---

## Telegram commands

Once Telegram is configured, you can also manage `config.yaml` remotely by messaging your bot commands instead of hand-editing the file — as long as the [command listener](#linux-cron) is scheduled. Send `/help` to the bot at any time for the full list. Commands:

| Command | Effect |
|---|---|
| `/add_position id=<id> symbol=<symbol> entry_price=<price> shares=<qty>` | Add a new bought-position lot. All 4 fields are required. |
| `/remove_position id=<id>` | Remove a bought-position lot by id. |
| `/add_watch <SYMBOL>` | Add a symbol to the high-growth watchlist. |
| `/remove_watch <SYMBOL>` | Remove a symbol from the high-growth watchlist. |
| `/status_frequency <every_run\|weekly\|disabled>` | Change how often the status message is sent. |
| `/mode <all\|only_exit\|disabled>` | Change which alerts fire: all, exit-only, or none. |
| `/help` | List all commands. |

The bot replies immediately to confirm your message was received, then replies again with the result (success or a specific error — e.g. missing fields, duplicate id). Only messages from the chat ID in your `.env` are accepted.

---

## Scheduling

The analysis runs **once per day at 19:00 (7 PM), weekdays only (Monday–Friday)**. The Telegram command listener, if used, runs on its own, much more frequent schedule (e.g. every 1-2 minutes) so replies feel responsive. Configure both in cron or Task Scheduler (see below); the app does not check the day of week.

### Linux (cron)

```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```

Or add to crontab manually (use the venv’s Python). Example: analysis weekdays only (Mon–Fri) at 19:00, command listener every 2 minutes:

```bash
0 19 * * 1-5 cd /path/to/PatateAlerts && .venv/bin/python src/main.py >> logs/cron.log 2>&1
*/2 * * * * cd /path/to/PatateAlerts && .venv/bin/python src/telegram_command_listener.py >> logs/telegram_commands_cron.log 2>&1
```

### Windows (Task Scheduler)

Run as Administrator:

```powershell
.\scripts\setup_task_scheduler.ps1
```

Or: `scripts\setup_task_scheduler.bat`

Configure the task to use the venv’s Python (e.g. `C:\path\to\PatateAlerts\.venv\Scripts\python.exe`), arguments `src/main.py`, and “Start in” = project directory.

---

## Run manually

Activate the virtual environment, then from the project directory:

```bash
python src/main.py
```

Logs go to `logs/app.log`. The app creates `data/` (SQLite) and `logs/` as needed.

---

## More information

- **[docs/REFERENCE.md](docs/REFERENCE.md)** — Architecture, design decisions, project structure, and configuration reference for contributors.
