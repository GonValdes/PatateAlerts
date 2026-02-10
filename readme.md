# Stock Alert Monitor

Python app that monitors a list of stocks and sends alerts when price-based conditions are met (high-growth entry signals and per-lot exit rules). Designed to run on a schedule (e.g. Raspberry Pi or Windows) with minimal setup.

---

## Setup

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Create and activate a virtual environment** (recommended)
   ```bash
   # Create
   python -m venv .venv

   # Activate: Linux/macOS
   source .venv/bin/activate

   # Activate: Windows (PowerShell)
   .venv\Scripts\Activate.ps1

   # Activate: Windows (Command Prompt)
   .venv\Scripts\activate.bat
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   - Copy `env.example` to `.env`
   - Add your Telegram bot token and chat ID if you use Telegram notifications

4. **Configure stocks**
   - **Update `config/config.yaml`** with your choices:
     - **Add stocks to monitor** — Under `stocks:`, list the symbols you want entry and tracking alerts for.
     - **Add bought positions** — Under `bought_positions:`, add each lot you own (unique `id`, `symbol`, `entry_price`, `shares`). The app will evaluate exit rules and notify you when stops are hit.
     - **Set settings** — Adjust scheduling, notification options, and data cache as needed in the same file.

   **You are responsible for keeping `config.yaml` up to date.** When you buy or sell in real life, add, remove, or update the corresponding entries in `config/config.yaml` (e.g. remove a lot after you’ve sold it). The app does not change your config.

For more detail on configuration and platform-specific setup (Telegram, cron, Task Scheduler), see **[docs/SETUP.md](docs/SETUP.md)**.

### Scheduling

Run the scheduler setup with your virtual environment in mind (see [docs/SETUP.md](docs/SETUP.md) for venv-aware examples).

- **Linux (cron):** Run `./scripts/setup_cron.sh` or add a cron entry that runs the project’s Python (e.g. `path/to/project/.venv/bin/python src/main.py`) from the project directory.
- **Windows:** Run `.\scripts\setup_task_scheduler.ps1` (PowerShell as Administrator) or use `scripts\setup_task_scheduler.bat`.

Details and examples are in [docs/SETUP.md](docs/SETUP.md).

### Run manually

Activate the virtual environment, then from the project directory:

```bash
python src/main.py
```

---

## More information

- **[docs/SETUP.md](docs/SETUP.md)** — Step-by-step setup (Telegram, cron, Task Scheduler, platform notes).
- **[docs/REFERENCE.md](docs/REFERENCE.md)** — Architecture, design decisions, project structure, and configuration reference for contributors.

#### Setting Up Telegram Notifications

To receive alerts via Telegram, you need to set up a bot and get your credentials:

**Step 1: Create a Telegram Bot**

1. Open Telegram and search for `@BotFather`
2. Start a chat with BotFather and send `/newbot`
3. Follow the prompts to name your bot (e.g., "Stock Alert Monitor")
4. BotFather will give you a **bot token** that looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
5. **Save this token** - you'll need it for the `.env` file

**Step 2: Get Your Chat ID**

1. Start a chat with your new bot (search for it by the name you gave it)
2. Send any message to your bot (e.g., `/start` or "Hello")
3. Open this URL in your browser (replace `YOUR_BOT_TOKEN` with your actual token):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for a JSON response that contains `"chat":{"id":123456789}`
5. The number after `"id":` is your **chat ID** (it's a numeric value, not a username)
6. **Save this chat ID** - you'll need it for the `.env` file

**Step 3: Configure `.env` File**

1. Edit `.env` and replace the placeholder values:
   ```env
   TELEGRAM_BOT_TOKEN="your_bot_token_here"
   TELEGRAM_CHAT_ID="your_chat_id_here"
   ```
   
   **Important:**
   - The bot token should be in quotes and look like: `"123456789:ABCdef..."`
   - The chat ID should be in quotes and be a numeric value: `"123456789"`
   - Do NOT include the `@` symbol or bot username

3. Save the `.env` file

**Step 4: Test Telegram Connection**

Activate the virtual environment, then run:
```bash
python src/main.py
```

You should receive a test message in Telegram when the monitor starts. If you don't:
- Check the logs for error messages
- Verify your bot token is correct
- Verify your chat ID is numeric (not a username)
- Make sure you've sent at least one message to your bot

### Running Manually

