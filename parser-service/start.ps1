$ErrorActionPreference = "Stop"

# Ensure we are in the parser-service directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Activate the virtual environment if it exists
if (Test-Path "..\venv311\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & "..\venv311\Scripts\Activate.ps1"
} elseif (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & ".\.venv\Scripts\Activate.ps1"
} elseif (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "No virtual environment found. Make sure dependencies are installed." -ForegroundColor Yellow
}

Write-Host "Starting Parser Service on http://localhost:8010" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

# Start the uvicorn server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
