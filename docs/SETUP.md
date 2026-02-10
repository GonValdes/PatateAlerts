# Setup Guide

## Cross-Platform Support

This application runs on both **Linux** and **Windows**. Use a **Python virtual environment** so dependencies stay isolated and the same Python is used by cron or Task Scheduler.

### Python Code
- Uses `pathlib.Path` for cross-platform file paths
- All file operations are platform-independent
- SQLite database works identically on both platforms

### Virtual Environment

Create and activate a venv in the project directory before installing dependencies or running the app:

```bash
# Create (run from project root)
python -m venv .venv
```

**Activate:**

| Platform | Command |
|----------|---------|
| Linux / macOS | `source .venv/bin/activate` |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (Command Prompt) | `.venv\Scripts\activate.bat` |

When the venv is active, your prompt usually shows `(.venv)`. Use `python` and `pip` as usual; they refer to the venv.

### Platform-Specific Setup

#### Linux Setup
1. Create and activate the virtual environment (see above).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up cron (use the venv’s Python so scheduled runs use the same environment):
   ```bash
   chmod +x scripts/setup_cron.sh
   ./scripts/setup_cron.sh
   ```
   If editing crontab manually, run the script with the venv interpreter, e.g.:
   ```bash
   0 9,12,15,18 * * * cd /path/to/PatateAlerts && .venv/bin/python src/main.py >> logs/cron.log 2>&1
   ```

#### Windows Setup
1. Create and activate the virtual environment (see above).
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Set up Task Scheduler (PowerShell as Administrator):
   ```powershell
   .\scripts\setup_task_scheduler.ps1
   ```
   Configure the task to use the venv’s Python, e.g. `C:\path\to\PatateAlerts\.venv\Scripts\python.exe` with arguments `src/main.py` and “Start in” set to the project directory.

   Or use the batch script:
   ```cmd
   scripts\setup_task_scheduler.bat
   ```

