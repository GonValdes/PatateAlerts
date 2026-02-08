# Stock Alert Monitor

Python app that monitors a list of stocks and sends alerts when price-based conditions are met (high-growth entry signals and per-lot exit rules). Designed to run on a schedule (e.g. Raspberry Pi or Windows) with minimal setup.

---

## Setup

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   - Copy `env.example` to `.env`
   - Add your Telegram bot token and chat ID if you use Telegram notifications

3. **Configure stocks**
   - **Update `config/config.yaml`** with your choices:
     - **Add stocks to monitor** — Under `stocks:`, list the symbols you want entry and tracking alerts for.
     - **Add bought positions** — Under `bought_positions:`, add each lot you own (unique `id`, `symbol`, `entry_price`, `shares`). The app will evaluate exit rules and notify you when stops are hit.
     - **Set settings** — Adjust scheduling, notification options, and data cache as needed in the same file.

   **You are responsible for keeping `config.yaml` up to date.** When you buy or sell in real life, add, remove, or update the corresponding entries in `config/config.yaml` (e.g. remove a lot after you’ve sold it). The app does not change your config.

For more detail on configuration and platform-specific setup (Telegram, cron, Task Scheduler), see **[docs/SETUP.md](docs/SETUP.md)**.

### Scheduling

- **Linux (cron):** Run `./scripts/setup_cron.sh` or add a cron entry that runs `python src/main.py` from the project directory at your desired times.
- **Windows:** Run `.\scripts\setup_task_scheduler.ps1` (PowerShell as Administrator) or use `scripts\setup_task_scheduler.bat`.

Details and examples are in [docs/SETUP.md](docs/SETUP.md).

### Run manually

To test without the scheduler:

```bash
python src/main.py
```

---

## More information

- **[docs/SETUP.md](docs/SETUP.md)** — Step-by-step setup (Telegram, cron, Task Scheduler, platform notes).
- **[docs/REFERENCE.md](docs/REFERENCE.md)** — Architecture, design decisions, project structure, and configuration reference for contributors.
