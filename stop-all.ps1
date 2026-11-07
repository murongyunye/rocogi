# stop-all.ps1 - stop only the PIDs recorded by start-all.ps1.
# Exact PID matching (including child PIDs by ParentProcessId); never name matching.
$ErrorActionPreference = 'Continue'

$Root = $PSScriptRoot
$LogDir = Join-Path $Root 'logs'
$PidFile = Join-Path $LogDir 'pids.json'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
$LogPath = Join-Path $LogDir "stop-all-$Stamp.log"

function Write-Log([string]$Text) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Text
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-ChildPids([int]$ParentId) {
    $result = @()
    $kids = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId" -ErrorAction SilentlyContinue)
    foreach ($k in $kids) {
        $result += (Get-ChildPids ([int]$k.ProcessId))
        $result += [int]$k.ProcessId
    }
    return @($result)
}

$Rows = @()
$Remaining = @()

if (-not (Test-Path $PidFile)) {
    Write-Log "pids.json not found; nothing recorded by start-all.ps1"
    Write-Host 'No PIDs recorded. Nothing to stop.'
    exit 0
}

try {
    $doc = Get-Content -Path $PidFile -Raw | ConvertFrom-Json
} catch {
    Write-Log "pids.json unreadable: $($_.Exception.Message)"
    exit 1
}

$entries = @($doc.entries)
Write-Log "stop-all $Stamp entries=$($entries.Count)"

foreach ($e in $entries) {
    $pidValue = [int]$e.pid
    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if (-not $proc) {
        $Rows += [pscustomobject]@{ service = $e.name; pid = $pidValue; status = 'SKIPPED'; note = 'already stopped' }
        Write-Log "$($e.name) pid=$pidValue already stopped"
        continue
    }

    $startMismatch = $true
    try {
        $stored = [datetime]$e.startTime
        $delta = [math]::Abs(($proc.StartTime - $stored).TotalSeconds)
        if ($delta -le 5) { $startMismatch = $false }
    } catch { }

    if ($startMismatch) {
        $Rows += [pscustomobject]@{ service = $e.name; pid = $pidValue; status = 'FAIL'; note = 'PID reused or start time mismatch; not stopped' }
        $Remaining += $e
        Write-Log "$($e.name) pid=$pidValue FAIL start-time mismatch; not stopped"
        continue
    }

    $children = @(Get-ChildPids $pidValue)
    foreach ($cid in $children) {
        Stop-Process -Id $cid -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue

    $deadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 300
    }

    $left = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($left) {
        $Rows += [pscustomobject]@{ service = $e.name; pid = $pidValue; status = 'FAIL'; note = "still alive; children stopped=$($children.Count)" }
        $Remaining += $e
        Write-Log "$($e.name) pid=$pidValue FAIL still alive"
    } else {
        $Rows += [pscustomobject]@{ service = $e.name; pid = $pidValue; status = 'PASS'; note = "stopped; children=$($children.Count)" }
        Write-Log "$($e.name) pid=$pidValue stopped (children=$($children.Count))"
    }
}

# Keep only entries that could not be stopped; never keep PID reuse hazards.
$pidDoc = [pscustomobject]@{
    generatedAt = (Get-Date).ToString('o')
    script = 'stop-all.ps1'
    stoppedAt = (Get-Date).ToString('o')
    entries = @($Remaining)
}
$pidDoc | ConvertTo-Json -Depth 6 | Set-Content -Path $PidFile -Encoding UTF8

$table = $Rows | Format-Table service, pid, status, note -AutoSize | Out-String
Write-Host $table
Add-Content -Path $LogPath -Value $table -Encoding UTF8

$failed = @($Rows | Where-Object { $_.status -eq 'FAIL' })
if ($failed.Count -gt 0) {
    Write-Log "result FAIL ($($failed.Count) pid(s))"
    exit 1
}
Write-Log 'result PASS'
exit 0
