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

**You are responsible for keeping `config.yaml` up to date.** When you buy or sell in real life, add, remove, or update entries in `config/config.yaml` (e.g. remove a lot after you’ve sold). The app does not change your config.

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

**4. Test** — With the venv activated, run `python src/main.py`. You should get a message in Telegram. If not: check logs, verify token and numeric chat ID, and that you’ve sent at least one message to the bot.

---

## Scheduling

The analysis runs **once per day at 19:00 (7 PM), weekdays only (Monday–Friday)**. Configure this in cron or Task Scheduler (see below); the app does not check the day of week.

### Linux (cron)

```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```

Or add to crontab manually (use the venv’s Python). Example: weekdays only (Mon–Fri) at 19:00:

```bash
0 19 * * 1-5 cd /path/to/PatateAlerts && .venv/bin/python src/main.py >> logs/cron.log 2>&1
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
