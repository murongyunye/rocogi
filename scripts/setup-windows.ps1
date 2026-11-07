#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Rocogi Windows setup" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r backend\requirements.txt
& $venvPython -m pip install pywin32 interception-python

if (-not (Test-Path "frontend\dist\index.html")) {
    Push-Location frontend
    npm install --no-audit --no-fund
    npm run build
    Pop-Location
}

Write-Host ""
Write-Host "Dependencies are ready." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Install the Interception driver (see docs/windows-setup.md)."
Write-Host "  2. Start the server as Administrator:"
Write-Host "       .venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8787"
Write-Host "  3. Open http://127.0.0.1:8787 and switch Settings -> target to Windows."
Write-Host ""
