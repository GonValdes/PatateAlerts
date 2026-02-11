#!/bin/bash
# Example cron setup script for stock alert monitor
# 
# This script helps set up a cron job to run the stock monitor
# Usage: ./scripts/setup_cron.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_PATH=$(which python3)

if [ -z "$PYTHON_PATH" ]; then
    echo "Error: python3 not found in PATH"
    exit 1
fi

MAIN_SCRIPT="$PROJECT_DIR/src/main.py"

if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "Error: main.py not found at $MAIN_SCRIPT"
    exit 1
fi

# Run once per day at 19:00 (7 PM)
CRON_SCHEDULE="0 19 * * *"

CRON_LINE="$CRON_SCHEDULE cd $PROJECT_DIR && $PYTHON_PATH $MAIN_SCRIPT >> logs/cron.log 2>&1"

echo "Setting up cron job..."
echo "Schedule: $CRON_SCHEDULE"
echo "Command: $CRON_LINE"
echo ""
echo "To add this cron job, run:"
echo "crontab -e"
echo ""
echo "Then add this line:"
echo "$CRON_LINE"
echo ""
echo "Or run this command to add it automatically:"
echo "(crontab -l 2>/dev/null; echo \"$CRON_LINE\") | crontab -"
