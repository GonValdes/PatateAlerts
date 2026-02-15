@echo off
REM Windows Task Scheduler setup script (batch version)
REM Run this script as Administrator
REM Usage: scripts\setup_task_scheduler.bat

setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
cd /d "%PROJECT_DIR%"

REM Find Python
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where python3 >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=python3"
    ) else (
        echo Error: Python not found in PATH
        exit /b 1
    )
)

set "MAIN_SCRIPT=%PROJECT_DIR%\src\main.py"
if not exist "%MAIN_SCRIPT%" (
    echo Error: main.py not found at %MAIN_SCRIPT%
    exit /b 1
)

echo.
echo Setting up Windows Task Scheduler for Stock Alert Monitor
echo.
echo Python: %PYTHON_CMD%
echo Script: %MAIN_SCRIPT%
echo.
echo This will create a scheduled task that runs on weekdays (Mon-Fri) at 7:00 PM (19:00).
echo.
echo Note: For easier setup, use the PowerShell script instead:
echo   .\scripts\setup_task_scheduler.ps1
echo.
echo To manually create the task (weekdays at 19:00), use Task Scheduler GUI or run:
echo   schtasks /create /tn "StockAlertMonitor" /tr "%PYTHON_CMD% \"%MAIN_SCRIPT%\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 19:00 /ru SYSTEM
echo.

pause
