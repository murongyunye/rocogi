# Build the headless Rocogi engines as Windows .exe files.
# Run from the repository root: powershell -ExecutionPolicy Bypass -File scripts/build-engines.ps1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Pip = Join-Path $Root ".venv\Scripts\pip.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
  $Pip = "pip"
}

& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[install] pyinstaller"
  & $Pip install -q pyinstaller
}

$Dist = Join-Path $Root "dist\engines"
$Work = Join-Path $Root "build\engines"
$Spec = Join-Path $Root "build\specs"
New-Item -ItemType Directory -Force -Path $Dist, $Work, $Spec | Out-Null

$Excludes = @(
  "--exclude-module", "fastapi",
  "--exclude-module", "uvicorn",
  "--exclude-module", "websockets",
  "--exclude-module", "starlette",
  "--exclude-module", "pydantic",
  "--exclude-module", "app.api",
  "--exclude-module", "app.main",
  "--exclude-module", "app.harness"
)
$Data = @("--add-data", ((Join-Path $Root "data") + ";data"))
$Vendor = @(
  "--paths", "backend/vendor/nrc_ai",
  "--hidden-import", "src.battle",
  "--hidden-import", "src.mcts",
  "--hidden-import", "src.team_builder",
  "--hidden-import", "src.models",
  "--hidden-import", "src.pokemon_db",
  "--hidden-import", "src.skill_db",
  "--hidden-import", "src.effect_engine",
  "--hidden-import", "src.effect_models",
  "--hidden-import", "src.effect_data",
  "--hidden-import", "src.skill_effects_generated",
  "--hidden-import", "src.pokemon_nature_table",
  "--add-data", ((Join-Path $Root "backend/vendor/nrc_ai/data") + ";backend/vendor/nrc_ai/data")
)

function Build-Engine {
  param(
    [string]$Name,
    [string]$Entry,
    [string]$Hidden,
    [string[]]$Extra
  )
  Write-Host "[build] $Name"
  $arguments = @(
    "-m", "PyInstaller",
    "--noconfirm", "--clean", "--onefile",
    "--name", $Name,
    "--paths", "backend",
    "--hidden-import", $Hidden
  ) + $Excludes + $Extra + @(
    "--distpath", $Dist,
    "--workpath", (Join-Path $Work $Name),
    "--specpath", $Spec,
    (Join-Path "packaging\entries" "$Entry.py")
  )
  & $Python @arguments | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed for $Name"
  }
  Write-Host "[done] $(Join-Path $Dist "$Name.exe")"
}

Build-Engine -Name "RocogiSense" -Entry "engine_sense" -Hidden "app.engine_sense" -Extra $Data
Build-Engine -Name "RocogiInput" -Entry "engine_input" -Hidden "app.engine_input" -Extra @()
Build-Engine -Name "RocogiSift" -Entry "engine_sift" -Hidden "app.engine_sift" -Extra $Data
Build-Engine -Name "RocogiBattle" -Entry "engine_battle" -Hidden "app.engine_battle" -Extra ($Data + $Vendor)
Build-Engine -Name "RocogiFlow" -Entry "engine_flow" -Hidden "app.engine_flow" -Extra ($Data + $Vendor)
Build-Engine -Name "RocogiEngine" -Entry "engine_core" -Hidden "app.engine_core" -Extra ($Data + $Vendor)

Write-Host ""
Write-Host "Engine executables: $Dist"
Get-ChildItem (Join-Path $Dist "Rocogi*.exe") | ForEach-Object {
  $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
  "$hash  $($_.Name)"
} | Set-Content (Join-Path $Dist "checksums.txt")
Get-ChildItem $Dist | Format-Table Name, Length, LastWriteTime
