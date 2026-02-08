# Setup Guide

## Cross-Platform Support

This application runs on both **Linux** and **Windows**.

### Python Code
- Uses `pathlib.Path` for cross-platform file paths
- All file operations are platform-independent
- SQLite database works identically on both platforms

### Platform-Specific Setup

#### Linux Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up cron:
   ```bash
   chmod +x scripts/setup_cron.sh
   ./scripts/setup_cron.sh
   ```

#### Windows Setup
1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

2. Set up Task Scheduler (PowerShell as Administrator):
   ```powershell
   .\scripts\setup_task_scheduler.ps1
   ```

   Or use batch script:
   ```cmd
   scripts\setup_task_scheduler.bat
   ```

### Configuration

Both platforms use the same configuration:
- `config/config.yaml` - Stock list and thresholds
- `.env` - Telegram credentials (copy from `env.example`)

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

Run the application:
```bash
python src/main.py
```

You should receive a test message in Telegram when the monitor starts. If you don't:
- Check the logs for error messages
- Verify your bot token is correct
- Verify your chat ID is numeric (not a username)
- Make sure you've sent at least one message to your bot

### Running Manually

Test the application on either platform:
```bash
# Linux
python3 src/main.py

# Windows
python src/main.py
```

### File Paths

All paths in the code use forward slashes (`/`) which work on both platforms thanks to Python's `pathlib`. The application will create:
- `data/` directory for SQLite database
- `logs/` directory for log files

These work identically on both Linux and Windows.
