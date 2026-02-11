# Windows Task Scheduler setup script for stock alert monitor
# Run this script in PowerShell (as Administrator for system-wide scheduling)
# Usage: .\scripts\setup_task_scheduler.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $PythonPath) {
    $PythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}

if (-not $PythonPath) {
    Write-Host "Error: Python not found in PATH. Please install Python 3.11+ and ensure it's in your PATH." -ForegroundColor Red
    exit 1
}

$MainScript = Join-Path $ProjectDir "src\main.py"

if (-not (Test-Path $MainScript)) {
    Write-Host "Error: main.py not found at $MainScript" -ForegroundColor Red
    exit 1
}

$LogDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$TaskName = "StockAlertMonitor"
$TaskDescription = "Runs stock alert monitor once per day at 7:00 PM"

$Trigger = New-ScheduledTaskTrigger -Daily -At "7:00PM"

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$MainScript`"" -WorkingDirectory $ProjectDir

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Write-Host "Creating scheduled task: $TaskName" -ForegroundColor Green
Write-Host "Python: $PythonPath" -ForegroundColor Cyan
Write-Host "Script: $MainScript" -ForegroundColor Cyan
Write-Host "Schedule: Daily at 7:00 PM (19:00)" -ForegroundColor Cyan
Write-Host ""

try {
    # Check if task already exists
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    
    if ($ExistingTask) {
        Write-Host "Task already exists. Updating..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    Register-ScheduledTask -TaskName $TaskName -Description $TaskDescription `
        -Action $Action -Trigger $Trigger `
        -Settings $Settings -RunLevel Highest
    
    Write-Host "Task scheduled successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To view the task:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To remove the task:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false" -ForegroundColor Cyan
}
catch {
    Write-Host "Error creating scheduled task: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Note: You may need to run PowerShell as Administrator to create scheduled tasks." -ForegroundColor Yellow
    exit 1
}
