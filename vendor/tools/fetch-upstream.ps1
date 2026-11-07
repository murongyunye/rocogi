# fetch-upstream.ps1
# 按 vendor/upstream_sources.json 记录的 commit，把上游完整源码重新拉取到
# vendor\_restore\<repo>。绝不写入 vendor\<repo>（运行时子集）。
#
# 用法:
#   .\fetch-upstream.ps1 -List
#   .\fetch-upstream.ps1 -Repo Pacific-shark-roco-balance-lab
#   .\fetch-upstream.ps1 -Repo yottaapp-yotta,Adolph321-Adolph
#   .\fetch-upstream.ps1 -All
#   .\fetch-upstream.ps1 -All -DryRun
#   .\fetch-upstream.ps1 -Repo ... -Force   # 覆盖已存在的 _restore\<repo>

[CmdletBinding()]
param(
    [string[]]$Repo,
    [switch]$All,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$List
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$SourcesPath = Join-Path $Root 'vendor\upstream_sources.json'
$RestoreRoot = Join-Path $Root 'vendor\_restore'
$GitExe = Join-Path $Root '.toolchain\git\cmd\git.exe'
if (-not (Test-Path $GitExe)) { $GitExe = 'git' }

function Fail([string]$msg) {
    Write-Host "  FAIL: $msg" -ForegroundColor Red
}

if (-not (Test-Path $SourcesPath)) {
    Write-Host "找不到来源清单: $SourcesPath" -ForegroundColor Red
    exit 2
}
$doc = Get-Content -Raw -Encoding UTF8 $SourcesPath | ConvertFrom-Json
$allRepos = @($doc.repos)

if ($List) {
    foreach ($r in $allRepos) {
        $c = if ($r.commit) { $r.commit } else { $r.commit_short }
        Write-Host ("{0,-46} {1,-12} {2,-8} {3}" -f $r.repo, $r.source_type, $c, $r.upstream_url)
    }
    exit 0
}

if ($All) {
    $targets = @($allRepos | Where-Object { $_.source_type -eq 'github' })
} elseif ($Repo) {
    $targets = @()
    foreach ($want in $Repo) {
        $hit = $allRepos | Where-Object { $_.repo -eq $want } | Select-Object -First 1
        if (-not $hit) {
            $hit = $allRepos | Where-Object { $_.repo -like "*$want*" } | Select-Object -First 1
        }
        if (-not $hit) {
            Fail "未知仓库 '$want'（用 -List 查看 16 个仓名）"
            continue
        }
        $targets += $hit
    }
} else {
    Write-Host "需要 -Repo <name>、-All 或 -List"
    exit 2
}

if (-not (Test-Path $RestoreRoot)) { New-Item -ItemType Directory -Force -Path $RestoreRoot | Out-Null }

$results = @()
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

foreach ($t in $targets) {
    $name = $t.repo
    $dest = Join-Path $RestoreRoot $name
    $destFull = [System.IO.Path]::GetFullPath($dest)
    $guard = [System.IO.Path]::GetFullPath($RestoreRoot) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $destFull.StartsWith($guard, [System.StringComparison]::OrdinalIgnoreCase)) {
        Fail "目标目录越界，拒绝写入: $destFull"
        continue
    }

    Write-Host ""
    Write-Host "[$name] $($t.source_type) $($t.commit) -> $destFull"

    if ($t.source_type -ne 'github') {
        Fail "非 git 源（上游为发布包）。重拉路径是自有仓库 archive/sift-map-tracker/，见 PUBLISH_SCOPE.md 第 6 节；本脚本不处理。"
        $results += [pscustomobject]@{ repo = $name; ok = $false; method = 'none'; error = 'non-git upstream (release package)' }
        continue
    }
    if ($DryRun) {
        Write-Host ("  DRY-RUN: git fetch {0} 的 {1} -> {2}" -f $t.upstream_url, $t.commit, $destFull)
        $results += [pscustomobject]@{ repo = $name; ok = $true; method = 'dry-run'; dest = $destFull }
        continue
    }
    if (Test-Path $dest) {
        if (-not $Force) {
            Fail "目标已存在（不覆盖）。加 -Force 才重建: $destFull"
            $results += [pscustomobject]@{ repo = $name; ok = $false; method = 'skip'; error = 'exists' }
            continue
        }
        Remove-Item -Recurse -Force $dest
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $method = 'git-fetch-sha'
    $err = $null
    try {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        & $GitExe init -q $dest 2>&1 | Out-Null
        & $GitExe -C $dest remote add origin $t.upstream_url 2>&1 | Out-Null
        $fetchOut = & $GitExe -C $dest fetch --depth 1 --no-tags origin $t.commit 2>&1
        if ($LASTEXITCODE -ne 0) { throw ("git fetch 失败: " + ($fetchOut -join ' ')) }
        $co = & $GitExe -C $dest checkout -q --detach FETCH_HEAD 2>&1
        if ($LASTEXITCODE -ne 0) { throw ("git checkout 失败: " + ($co -join ' ')) }
    } catch {
        $err = $_.Exception.Message
        # 回退：codeload zip（GitHub 允许按 commit 打包）
        try {
            if ($t.upstream_url -match '^https://github\.com/([^/]+)/([^/]+?)/?$') {
                $owner = $Matches[1]; $repoName = $Matches[2]
                $zipUrl = "https://codeload.github.com/$owner/$repoName/zip/$($t.commit)"
                $zip = Join-Path $env:TEMP ("rocogi-$name-$stamp.zip")
                Write-Host "  git 按 SHA 拉取失败，回退 codeload: $zipUrl"
                Invoke-WebRequest -Uri $zipUrl -OutFile $zip -UseBasicParsing
                if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
                Expand-Archive -Path $zip -DestinationPath $dest -Force
                $inner = Get-ChildItem $dest -Directory | Select-Object -First 1
                if ($inner) {
                    Get-ChildItem $inner.FullName -Force | Move-Item -Destination $dest -Force
                    Remove-Item -Recurse -Force $inner.FullName
                }
                Remove-Item -Force $zip
                $method = 'codeload-zip'
                $err = $null
            } else {
                throw
            }
        } catch {
            $err = $err + ' | 回退也失败: ' + $_.Exception.Message
        }
    }

    if ($err) {
        Fail $err
        if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
        $results += [pscustomobject]@{ repo = $name; ok = $false; method = $method; error = $err }
        continue
    }

    $actual = (& $GitExe -C $dest rev-parse HEAD 2>$null)
    $actual = ($actual | Select-Object -First 1).Trim()
    if ($actual -ne $t.commit) {
        Fail "commit 不一致: 期望 $($t.commit)，实得 $actual"
        $results += [pscustomobject]@{ repo = $name; ok = $false; method = $method; error = "commit mismatch: $actual" }
        continue
    }

    $files = Get-ChildItem -Path $dest -Recurse -File -Force |
        Where-Object { $_.FullName -notmatch '\\\.git\\' }
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    if (-not $bytes) { $bytes = 0 }
    $lines = foreach ($f in ($files | Sort-Object FullName)) {
        $rel = $f.FullName.Substring($destFull.Length + 1).Replace('\', '/')
        $h = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash.ToLower()
        "$rel|$($f.Length)|$h"
    }
    $joined = ($lines -join "`n")
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $digest = ([System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($joined))) -replace '-', '').ToLower()
    $sw.Stop()

    Write-Host ("  OK  {0} 文件 / {1:N1} MB / {2:N1}s / 内容摘要 {3}" -f $files.Count, ($bytes / 1MB), $sw.Elapsed.TotalSeconds, $digest.Substring(0, 16))
    $results += [pscustomobject]@{
        repo = $name; ok = $true; method = $method; commit = $actual;
        files = $files.Count; bytes = $bytes; digest_sha256 = $digest;
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1); dest = $destFull;
        upstream_url = $t.upstream_url
    }
}

$reportPath = Join-Path $RestoreRoot "fetch-report-$stamp.json"
[pscustomobject]@{
    generated_at = (Get-Date).ToString('o')
    dry_run = [bool]$DryRun
    git = $GitExe
    results = $results
} | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $reportPath

Write-Host ""
Write-Host "报告: $reportPath"
$bad = @($results | Where-Object { -not $_.ok })
Write-Host ("完成: {0} 成功 / {1} 失败" -f ($results.Count - $bad.Count), $bad.Count)
if ($bad.Count -gt 0) { exit 1 }
exit 0