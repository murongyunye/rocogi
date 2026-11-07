# start-all.ps1 - idempotent launcher for the Rocogi stack.
# Uses explicit toolchain paths only; it never edits system PATH or registry.
$ErrorActionPreference = 'Continue'

$Root = $PSScriptRoot
$Py = Join-Path $Root '.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe'
$Node = Join-Path $Root '.toolchain\node\node.exe'
$NodeDir = Join-Path $Root '.toolchain\node'
$GitDir = Join-Path $Root '.toolchain\git\cmd'
$VenvPy = Join-Path $Root '.venv\Scripts\python.exe'
$Vite = Join-Path $Root 'frontend\node_modules\vite\bin\vite.js'
$CBackend = Join-Path $Root 'backend-c\build2\rocogi-core.exe'
$WebUI = Join-Path $Root 'webui\server.py'
$SuiteCli = Join-Path $Root 'suite\kernel\cli.py'
$SuiteToml = Join-Path $Root 'suite\config\suite.toml'
$PidFile = Join-Path $Root 'logs\pids.json'

# Process-local environment only (does not change machine/user PATH).
$env:PATH = "$NodeDir;$GitDir;$env:PATH"
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$LogDir = Join-Path $Root 'logs'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
$LogPath = Join-Path $LogDir "start-all-$Stamp.log"
$CsvPath = Join-Path $LogDir "start-all-$Stamp.csv"

function Write-Log([string]$Text) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Text
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-PortOwner([int]$Port) {
    $c = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return [int]$c.OwningProcess }
    return 0
}

function Get-JsonVersion([string]$Text) {
    try { return [string](($Text | ConvertFrom-Json).version) } catch { return '-' }
}

function Get-SuiteVersion() {
    $m = Select-String -Path $SuiteToml -Pattern '^\s*version\s*=\s*"([^"]+)"' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($m) { return $m.Matches[0].Groups[1].Value }
    return '-'
}

function Wait-Http([int]$Port, [string]$Path, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    $lastError = ''
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port$Path" -TimeoutSec 3
            return [pscustomobject]@{ code = [int]$r.StatusCode; body = [string]$r.Content; error = '' }
        } catch {
            $lastError = $_.Exception.Message
            Start-Sleep -Milliseconds 500
        }
    }
    return [pscustomobject]@{ code = 0; body = ''; error = $lastError }
}

function Start-Svc([string]$Name, [string]$Exe, [string[]]$ArgList, [string]$Cwd) {
    $out = Join-Path $LogDir "start-all-$Stamp-$Name.out.log"
    $err = Join-Path $LogDir "start-all-$Stamp-$Name.err.log"
    $p = Start-Process -FilePath $Exe -ArgumentList $ArgList -WorkingDirectory $Cwd `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
    return [pscustomobject]@{ pid = [int]$p.Id; out = $out; err = $err }
}

# One process snapshot for all conflict checks.
$AllProcs = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
function Find-ServiceProcs([string]$Name) {
    switch ($Name) {
        'python-backend' {
            return @($AllProcs | Where-Object {
                $_.Name -eq 'python.exe' -and $_.CommandLine -like '*backend.app.main*' -and $_.CommandLine -like '*8787*'
            })
        }
        'c-backend' {
            return @($AllProcs | Where-Object {
                $_.Name -eq 'rocogi-core.exe' -and $_.CommandLine -like '*--port*8788*'
            })
        }
        'vite' {
            return @($AllProcs | Where-Object {
                $_.Name -eq 'node.exe' -and $_.CommandLine -like '*vite*' -and $_.CommandLine -like '*5173*'
            })
        }
        'webui' {
            return @($AllProcs | Where-Object {
                $_.Name -eq 'python.exe' -and $_.CommandLine -like '*webui*server.py*'
            })
        }
        'suite' {
            return @($AllProcs | Where-Object {
                $_.Name -eq 'python.exe' -and $_.CommandLine -like '*suite\kernel\cli.py*' -and $_.CommandLine -like '*--run-id*'
            })
        }
    }
    return @()
}

# Preserve only PIDs previously recorded by this script and still alive.
$Existing = @()
if (Test-Path $PidFile) {
    try {
        $doc = Get-Content -Path $PidFile -Raw | ConvertFrom-Json
        foreach ($e in @($doc.entries)) {
            $proc = Get-Process -Id ([int]$e.pid) -ErrorAction SilentlyContinue
            if ($proc) {
                $delta = [math]::Abs(($proc.StartTime - ([datetime]$e.startTime)).TotalSeconds)
                if ($delta -le 5) { $Existing += $e }
            }
        }
    } catch {
        Write-Log "pids.json unreadable, starting a fresh record: $($_.Exception.Message)"
    }
}

$Rows = @()
$Entries = @($Existing)
function Add-Row($Service, $Port, $Status, $Http, $Version, $ProcessId, $RunId, $Note, $Log) {
    $script:Rows += [pscustomobject]@{
        service = $Service
        port    = $Port
        status  = $Status
        http    = $Http
        version = $Version
        pid     = $ProcessId
        runId   = $RunId
        note    = $Note
        log     = $Log
    }
}

function Record-Entry([string]$Name, [int]$Port, [int]$ProcessId, [string]$RunId) {
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    $started = if ($proc) { $proc.StartTime.ToString('o') } else { (Get-Date).ToString('o') }
    $script:Entries = @($script:Entries | Where-Object { $_.name -ne $Name })
    $script:Entries += [pscustomobject]@{
        name = $Name
        port = $Port
        pid = $ProcessId
        startTime = $started
        runId = $RunId
        script = 'start-all.ps1'
    }
}

Write-Log "start-all $Stamp"
Write-Log "root=$Root"
Write-Log "python=$Py"

# ---------------------------------------------------------------------------
# Preflight: 解释器/依赖缺失时先给出可执行的修复命令，而不是让 Start-Process 抛异常
# ---------------------------------------------------------------------------
$Missing = @()
if (-not (Test-Path $VenvPy)) {
    $Missing += 'python venv 缺失 → .\.venv\Scripts\python.exe -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt'
}
if (-not (Test-Path $Node)) {
    $Missing += 'Node 缺失 → 安装 Node 20+，或把便携版放回 .toolchain\node'
}
if (-not (Test-Path $Py)) {
    $Missing += '便携 Python 缺失 → 放回 .toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe，或改 start-all.ps1 顶部的 $Py 指向系统 python'
}
if (-not (Test-Path $Vite)) {
    $Missing += '前端依赖缺失 → cd frontend; npm install'
}
if ($Missing.Count -gt 0) {
    foreach ($m in $Missing) { Write-Log "MISSING $m" }
    Write-Log "result FAIL ($($Missing.Count) prerequisite(s) missing)"
    exit 2
}

# ---------------------------------------------------------------------------
# 8787 Python backend
# ---------------------------------------------------------------------------
$name = 'python-backend'; $port = 8787
$owner = Get-PortOwner $port
$svcProcs = @(Find-ServiceProcs $name)
if ($owner -gt 0) {
    $h = Wait-Http $port '/api/health' 3
    $status = if ($h.code -eq 200) { 'SKIPPED' } else { 'FAIL' }
    Add-Row $name $port $status $h.code (Get-JsonVersion $h.body) $owner '' 'already listening' ''
    Write-Log "$name already listening on $port (pid=$owner http=$($h.code))"
} elseif ($svcProcs.Count -gt 0) {
    $pids = ($svcProcs | ForEach-Object { $_.ProcessId }) -join ','
    Add-Row $name $port 'CONFLICT' 0 '-' $pids '' "process exists but port $port is closed; pids=$pids" ''
    Write-Log "CONFLICT ${name}: process(es) $pids exist but port $port is closed; not killing them"
} else {
    $s = Start-Svc 'python-backend' $VenvPy @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8787') $Root
    Record-Entry $name $port $s.pid ''
    $h = Wait-Http $port '/api/health' 45
    $status = if ($h.code -eq 200) { 'PASS' } else { 'FAIL' }
    Add-Row $name $port $status $h.code (Get-JsonVersion $h.body) $s.pid '' $(if ($status -eq 'PASS') { 'started' } else { "health timeout: $($h.error)" }) "$($s.out); $($s.err)"
    Write-Log "$name started pid=$($s.pid) http=$($h.code)"
}

# ---------------------------------------------------------------------------
# 8788 C backend
# ---------------------------------------------------------------------------
$name = 'c-backend'; $port = 8788
$owner = Get-PortOwner $port
$svcProcs = @(Find-ServiceProcs $name)
if (-not (Test-Path $CBackend)) {
    # 构建产物不入库（见 docs/PUBLISH_SCOPE.md）：缺失时记为 MISSING 并计入失败，提示先构建。
    Add-Row $name $port 'MISSING' 0 '-' '' '' 'rocogi-core.exe 未构建：先跑 scripts/build-rocogi-windows.ps1' ''
    Write-Log "$name skipped: $CBackend not found"
} elseif ($owner -gt 0) {
    $h = Wait-Http $port '/api/health' 3
    $status = if ($h.code -eq 200) { 'SKIPPED' } else { 'FAIL' }
    Add-Row $name $port $status $h.code (Get-JsonVersion $h.body) $owner '' 'already listening' ''
    Write-Log "$name already listening on $port (pid=$owner http=$($h.code))"
} elseif ($svcProcs.Count -gt 0) {
    $pids = ($svcProcs | ForEach-Object { $_.ProcessId }) -join ','
    Add-Row $name $port 'CONFLICT' 0 '-' $pids '' "process exists but port $port is closed; pids=$pids" ''
    Write-Log "CONFLICT ${name}: process(es) $pids exist but port $port is closed; not killing them"
} else {
    $s = Start-Svc 'c-backend' $CBackend @('--port','8788') (Join-Path $Root 'backend-c')
    Record-Entry $name $port $s.pid ''
    $h = Wait-Http $port '/api/health' 20
    $status = if ($h.code -eq 200) { 'PASS' } else { 'FAIL' }
    Add-Row $name $port $status $h.code (Get-JsonVersion $h.body) $s.pid '' $(if ($status -eq 'PASS') { 'started' } else { "health timeout: $($h.error)" }) "$($s.out); $($s.err)"
    Write-Log "$name started pid=$($s.pid) http=$($h.code)"
}

# ---------------------------------------------------------------------------
# 5173 Vite dev server
# ---------------------------------------------------------------------------
$name = 'vite'; $port = 5173
$owner = Get-PortOwner $port
$svcProcs = @(Find-ServiceProcs $name)
if ($owner -gt 0) {
    $h = Wait-Http $port '/' 3
    $pkgVersion = '-'
    try { $pkgVersion = [string]((Get-Content (Join-Path $Root 'frontend\package.json') -Raw | ConvertFrom-Json).version) } catch {}
    $status = if ($h.code -eq 200) { 'SKIPPED' } else { 'FAIL' }
    Add-Row $name $port $status $h.code $pkgVersion $owner '' 'already listening' ''
    Write-Log "$name already listening on $port (pid=$owner http=$($h.code))"
} elseif ($svcProcs.Count -gt 0) {
    $pids = ($svcProcs | ForEach-Object { $_.ProcessId }) -join ','
    Add-Row $name $port 'CONFLICT' 0 '-' $pids '' "process exists but port $port is closed; pids=$pids" ''
    Write-Log "CONFLICT ${name}: process(es) $pids exist but port $port is closed; not killing them"
} else {
    $s = Start-Svc 'vite' $Node @($Vite,'--host','0.0.0.0','--port','5173') (Join-Path $Root 'frontend')
    Record-Entry $name $port $s.pid ''
    $h = Wait-Http $port '/' 30
    $status = if ($h.code -eq 200) { 'PASS' } else { 'FAIL' }
    Add-Row $name $port $status $h.code '-' $s.pid '' $(if ($status -eq 'PASS') { 'started' } else { "health timeout: $($h.error)" }) "$($s.out); $($s.err)"
    Write-Log "$name started pid=$($s.pid) http=$($h.code)"
}

# ---------------------------------------------------------------------------
# 8800 WebUI
# ---------------------------------------------------------------------------
$name = 'webui'; $port = 8800
$owner = Get-PortOwner $port
$svcProcs = @(Find-ServiceProcs $name)
if (-not (Test-Path $WebUI)) {
    # webui/ 属本机目录，不入库（见 docs/PUBLISH_SCOPE.md）：缺失时记为 MISSING，不影响 8787/5173 主链路。
    Add-Row $name $port 'MISSING' 0 '-' '' '' 'webui/server.py 缺失（本机目录，不入库，可跳过）' ''
    Write-Log "$name skipped: $WebUI not found"
} elseif ($owner -gt 0) {
    $h = Wait-Http $port '/' 3
    $status = if ($h.code -eq 200) { 'SKIPPED' } else { 'FAIL' }
    Add-Row $name $port $status $h.code (Get-SuiteVersion) $owner '' 'already listening' ''
    Write-Log "$name already listening on $port (pid=$owner http=$($h.code))"
} elseif ($svcProcs.Count -gt 0) {
    $pids = ($svcProcs | ForEach-Object { $_.ProcessId }) -join ','
    Add-Row $name $port 'CONFLICT' 0 '-' $pids '' "process exists but port $port is closed; pids=$pids" ''
    Write-Log "CONFLICT ${name}: process(es) $pids exist but port $port is closed; not killing them"
} else {
    $s = Start-Svc 'webui' $Py @($WebUI) $Root
    Record-Entry $name $port $s.pid ''
    $h = Wait-Http $port '/' 25
    $status = if ($h.code -eq 200) { 'PASS' } else { 'FAIL' }
    Add-Row $name $port $status $h.code (Get-SuiteVersion) $s.pid '' $(if ($status -eq 'PASS') { 'started' } else { "health timeout: $($h.error)" }) "$($s.out); $($s.err)"
    Write-Log "$name started pid=$($s.pid) http=$($h.code)"
}

# ---------------------------------------------------------------------------
# Suite resident run (no port; wait for run evidence)
# ---------------------------------------------------------------------------
$name = 'suite'; $port = 'n/a'
$svcProcs = @(Find-ServiceProcs $name)
if ($svcProcs.Count -gt 0) {
    $pidList = ($svcProcs | ForEach-Object { $_.ProcessId }) -join ','
    $runId = ''
    foreach ($m in $svcProcs) {
        $rx = [regex]::Match([string]$m.CommandLine, '--run-id\s+([^\s"]+)')
        if ($rx.Success) { $runId = $rx.Groups[1].Value; break }
    }
    Add-Row $name $port 'SKIPPED' '-' (Get-SuiteVersion) $pidList $runId 'resident run already present' ''
    Write-Log "$name already running (pids=$pidList runId=$runId)"
} else {
    $runId = Get-Date -Format 'yyyyMMdd-HHmmss'
    $s = Start-Svc 'suite' $Py @($SuiteCli,'run','--run-id',$runId,'--duration','0') $Root
    Record-Entry $name 0 $s.pid $runId
    $manifest = Join-Path $Root "suite\runs\$runId\manifest.json"
    $metrics = Join-Path $Root "suite\runs\$runId\metrics.json"
    $deadline = (Get-Date).AddSeconds(60)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        $proc = Get-Process -Id $s.pid -ErrorAction SilentlyContinue
        if (-not $proc) { break }
        if ((Test-Path $manifest) -and (Test-Path $metrics)) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    $status = if ($ready) { 'PASS' } else { 'FAIL' }
    Add-Row $name $port $status '-' (Get-SuiteVersion) $s.pid $runId $(if ($ready) { "resident run $runId" } else { 'run evidence timeout' }) "$($s.out); $($s.err)"
    Write-Log "$name started pid=$($s.pid) runId=$runId ready=$ready"
}

# ---------------------------------------------------------------------------
# Persist PIDs and print summary
# ---------------------------------------------------------------------------
$pidDoc = [pscustomobject]@{
    generatedAt = (Get-Date).ToString('o')
    script = 'start-all.ps1'
    entries = @($Entries)
}
$pidDoc | ConvertTo-Json -Depth 6 | Set-Content -Path $PidFile -Encoding UTF8

$table = $Rows | Format-Table service, port, status, http, version, pid, note -AutoSize | Out-String
Write-Host $table
Add-Content -Path $LogPath -Value $table -Encoding UTF8
$Rows | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8
Write-Log "pids -> $PidFile"
Write-Log "log  -> $LogPath"

$failed = @($Rows | Where-Object { $_.status -in @('FAIL','CONFLICT','ERROR','MISSING') })
if ($failed.Count -gt 0) {
    Write-Log "result FAIL ($($failed.Count) service(s))"
    exit 1
}
Write-Log 'result PASS'
exit 0

