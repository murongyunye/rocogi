# Build Rocogi.exe on Windows with PyInstaller.
# The resulting exe bundles the backend, frontend/dist, data and the NRC_AI engine.
# Icon: packaging/rocogi.ico (generated from the Rocogi mascot).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r backend\requirements.txt
& $Python -m pip install pyinstaller pywin32 interception-python

if (-not (Test-Path "frontend\dist\index.html")) {
    Push-Location frontend
    npm install --no-audit --no-fund
    npm run build
    Pop-Location
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Rocogi `
    --icon "packaging\rocogi.ico" `
    --add-data "frontend\dist;frontend\dist" `
    --add-data "data;data" `
    --add-data "backend\vendor;backend\vendor" `
    --collect-all uvicorn `
    --collect-all websockets `
    --collect-all cv2 `
    --collect-all PIL `
    --hidden-import app.main `
    --distpath "dist" `
    --workpath "build\pyinstaller" `
    --specpath "build" `
    "packaging\rocogi_launcher.py"

Write-Host ""
Write-Host "Built: $Root\dist\Rocogi.exe" -ForegroundColor Green
Write-Host "Run as Administrator for Interception input. First launch may take a few seconds."
