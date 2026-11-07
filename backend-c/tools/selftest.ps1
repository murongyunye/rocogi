param(
    [int]$Port = 8788,
    [string]$WorkflowFile = ""
)

$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:$Port"
$script:failed = 0

function Show-Result {
    param([string]$Name, [int]$Status, [string]$Body)
    $ok = $Status -eq 200
    $mark = "FAIL"
    if ($ok) { $mark = "PASS" }
    if (-not $ok) { $script:failed = $script:failed + 1 }
    $snippet = $Body -replace "\s+", " "
    if ($snippet.Length -gt 140) { $snippet = $snippet.Substring(0, 140) + "..." }
    Write-Host ("[{0}] {1,-28} status={2} {3}" -f $mark, $Name, $Status, $snippet)
}

function Fail {
    param([string]$Message)
    Write-Host ("[FAIL] " + $Message)
    $script:failed = $script:failed + 1
}

Write-Host "rocogi-core self test @ $base"
Write-Host ("-" * 72)

$resp = Invoke-WebRequest -Uri "$base/api/health" -UseBasicParsing -TimeoutSec 10
Show-Result "/api/health" ([int]$resp.StatusCode) $resp.Content
if ($resp.Content -notmatch '"engine"\s*:\s*"c"') { Fail "health did not report engine=c" }

$resp = Invoke-WebRequest -Uri "$base/api/meta" -UseBasicParsing -TimeoutSec 10
Show-Result "/api/meta" ([int]$resp.StatusCode) $resp.Content
if ($resp.Content -notmatch '"pointCount"') { Fail "meta missing map.pointCount" }

$resp = Invoke-WebRequest -Uri "$base/api/nodes" -UseBasicParsing -TimeoutSec 10
Show-Result "/api/nodes" ([int]$resp.StatusCode) $resp.Content
$perl = [regex]::Match($resp.Content, '"count"\s*:\s*(\d+)')
$nodeCount = 0
if ($perl.Success) { $nodeCount = [int]$perl.Groups[1].Value }
if ($nodeCount -lt 8) { Fail ("node contract count too small: " + $nodeCount) }

$resp = Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 10
Show-Result "/ (SPA index)" ([int]$resp.StatusCode) $resp.Content
$ctype = [string]$resp.Headers["Content-Type"]
if ($ctype -notmatch "text/html") { Fail "index is not text/html" }

if ($WorkflowFile -eq "") {
    $WorkflowFile = Join-Path $PSScriptRoot "..\workflows\demo-basic.json"
}

if (Test-Path $WorkflowFile) {
    $payload = Get-Content $WorkflowFile -Raw -Encoding UTF8
    $resp = Invoke-WebRequest -Uri "$base/api/workflows/run" -Method POST -ContentType "application/json; charset=utf-8" -Body $payload -UseBasicParsing -TimeoutSec 10
    Show-Result "POST /api/workflows/run" ([int]$resp.StatusCode) $resp.Content
    if ($resp.Content -notmatch '"events"') { Fail "run result missing evidence.events" }
    $sm = [regex]::Match($resp.Content, '"steps"\s*:\s*(\d+)')
    $steps = 0
    if ($sm.Success) { $steps = [int]$sm.Groups[1].Value }
    if ($steps -lt 3) { Fail ("executed steps too small: " + $steps) }
} else {
    Fail ("workflow sample not found: " + $WorkflowFile)
}

Write-Host ("-" * 72)
if ($script:failed -eq 0) {
    Write-Host "RESULT: ALL PASS"
    exit 0
}
Write-Host ("RESULT: " + $script:failed + " FAILED")
exit 1
