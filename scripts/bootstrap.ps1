#!/usr/bin/env pwsh
# bootstrap.ps1 -- 检测本机环境与上游依赖，缺失时才获取。
#
# 为什么不把东西塞进仓库：vendor/、datasets/*.db、模型权重、截图、便携
# toolchain 都不入库（见 docs/PUBLISH_SCOPE.md）。缺了就按下面登记的来源
# 现取，取完落到 .toolchain\ 或 vendor\_restore\，都在 .gitignore 里。
#
# 用法:
#   .\scripts\bootstrap.ps1              # 只体检，打印 ok / miss 与修复命令
#   .\scripts\bootstrap.ps1 -Apply       # 缺失项自动执行能自动的部分
#   .\scripts\bootstrap.ps1 -Apply -Deep # 连模型权重一起（很慢，几百 MB）
#   .\scripts\bootstrap.ps1 -Json        # 机器可读输出，给 CI 用

[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$Deep,
    [switch]$Json
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$MinGitUrl = 'https://github.com/git-for-windows/git/releases/download/v2.56.0.4.windows.1/MinGit-2.56.0.4-64-bit.zip'
$NodeUrl = 'https://nodejs.org/dist/v24.21.0/node-v24.21.0-win-x64.zip'

$items = [System.Collections.Generic.List[object]]::new()

function Add-Item {
    param(
        [string]$Name,
        [string]$Kind,
        [bool]$Ok,
        [string]$Detail,
        [string]$Fix,          # 给用户看的命令
        [scriptblock]$Run      # -Apply 时执行的动作，可为 $null
    )
    $items.Add([pscustomobject]@{
        name   = $Name
        kind   = $Kind
        ok     = $Ok
        detail = $Detail
        fix    = $Fix
        run    = $Run
    })
}

function Test-AnyFile {
    param([string]$Path, [string]$Filter)
    if (-not (Test-Path $Path)) { return $false }
    return @(Get-ChildItem -Path $Path -Filter $Filter -File -ErrorAction SilentlyContinue).Count -gt 0
}

# --- 1. 便携 git ---------------------------------------------------------
$gitExe = Join-Path $Root '.toolchain\git\cmd\git.exe'
Add-Item -Name 'git (.toolchain)' -Kind 'toolchain' -Ok:(Test-Path $gitExe) `
    -Detail $(if (Test-Path $gitExe) { $gitExe } else { '未安装；vendor 拉取与提交都需要它' }) `
    -Fix 'scripts/bootstrap.ps1 -Apply' `
    -Run {
        $zip = Join-Path $env:TEMP 'MinGit.zip'
        Write-Host "  下载 $MinGitUrl" -ForegroundColor DarkGray
        Invoke-WebRequest -Uri $MinGitUrl -OutFile $zip -UseBasicParsing
        $dest = Join-Path $Root '.toolchain\git'
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Expand-Archive -Path $zip -DestinationPath $dest -Force
        Remove-Item $zip -Force -ErrorAction SilentlyContinue
        Write-Host "  解包到 $dest" -ForegroundColor DarkGray
    }

# --- 2. Python / uv / Node ----------------------------------------------
$pythonExe = Join-Path $Root '.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe'
if (-not (Test-Path $pythonExe)) { $pythonExe = Join-Path $Root '.venv\Scripts\python.exe' }
Add-Item -Name 'python' -Kind 'toolchain' -Ok:(Test-Path $pythonExe) `
    -Detail $(if (Test-Path $pythonExe) { $pythonExe } else { '没有 .toolchain\python 也没有 .venv' }) `
    -Fix 'scripts/fetch_toolchain.py' -Run { if (Test-Path $pythonExe) { & $pythonExe (Join-Path $Root 'scripts\fetch_toolchain.py') } }

$uvExe = Join-Path $Root '.toolchain\uv\uv.exe'
Add-Item -Name 'uv' -Kind 'toolchain' -Ok:(Test-Path $uvExe) -Detail $(if (Test-Path $uvExe) { $uvExe } else { '可选，仅加速装依赖' }) `
    -Fix 'scripts/fetch_toolchain.py' -Run $null

$nodeExe = Join-Path $Root '.toolchain\node\node.exe'
Add-Item -Name 'node' -Kind 'toolchain' -Ok:(Test-Path $nodeExe) `
    -Detail $(if (Test-Path $nodeExe) { $nodeExe } else { '前端构建需要 Node 22+' }) `
    -Fix "Invoke-WebRequest $NodeUrl -OutFile node.zip; Expand-Archive node.zip .toolchain" `
    -Run {
        $zip = Join-Path $env:TEMP 'node.zip'
        Invoke-WebRequest -Uri $NodeUrl -OutFile $zip -UseBasicParsing
        Expand-Archive -Path $zip -DestinationPath (Join-Path $Root '.toolchain\node-tmp') -Force
        Move-Item (Join-Path $Root '.toolchain\node-tmp\node-v24.21.0-win-x64\*') (Join-Path $Root '.toolchain\node') -Force
        Remove-Item (Join-Path $Root '.toolchain\node-tmp') -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item $zip -Force -ErrorAction SilentlyContinue
    }

# --- 3. Python venv + 前端依赖 ------------------------------------------
$venvPy = Join-Path $Root '.venv\Scripts\python.exe'
Add-Item -Name 'python venv' -Kind 'runtime' -Ok:(Test-Path $venvPy) `
    -Detail $(if (Test-Path $venvPy) { $venvPy } else { '跑后端需要 .venv' }) `
    -Fix 'scripts/setup-windows.ps1' -Run { & (Join-Path $Root 'scripts\setup-windows.ps1') }

$nodeModules = Join-Path $Root 'frontend\node_modules'
Add-Item -Name 'frontend deps' -Kind 'runtime' -Ok:(Test-Path $nodeModules) `
    -Detail $(if (Test-Path $nodeModules) { $nodeModules } else { 'vite/vue 依赖未安装' }) `
    -Fix 'cd frontend; pnpm install' -Run {
        Push-Location (Join-Path $Root 'frontend')
        try { & pnpm install } finally { Pop-Location }
    }

Add-Item -Name 'frontend dist' -Kind 'runtime' -Ok:(Test-Path (Join-Path $Root 'frontend\dist\index.html')) `
    -Detail $(if (Test-Path (Join-Path $Root 'frontend\dist\index.html')) { 'frontend\dist' } else { '后端要托管它；也可用 vite dev' }) `
    -Fix 'cd frontend; pnpm build' -Run {
        Push-Location (Join-Path $Root 'frontend')
        try { & pnpm build } finally { Pop-Location }
    }

# --- 4. vendor 上游（16 个仓库，按 commit 现取） -------------------------
$sourcesPath = Join-Path $Root 'vendor\upstream_sources.json'
if (Test-Path $sourcesPath) {
    $repos = @((Get-Content -Raw -Encoding UTF8 $sourcesPath | ConvertFrom-Json).repos)
    $missing = @()
    foreach ($r in $repos) {
        $dir = Join-Path $Root ("vendor\" + $r.repo)
        if (-not (Test-Path $dir)) { $missing += $r.repo }
    }
    Add-Item -Name "vendor ($($repos.Count) 个上游)" -Kind 'upstream' -Ok:($missing.Count -eq 0) `
        -Detail $(if ($missing.Count -eq 0) { '全部在位' } else { "缺 $($missing.Count) 个: " + ($missing[0..([Math]::Min(4, $missing.Count - 1))] -join ', ') }) `
        -Fix 'vendor/tools/fetch-upstream.ps1 -All' -Run {
            & (Join-Path $Root 'vendor\tools\fetch-upstream.ps1') -All
        }
} else {
    Add-Item -Name 'vendor' -Kind 'upstream' -Ok:$false -Detail '找不到 vendor\upstream_sources.json' -Fix 'git restore vendor' -Run $null
}

# --- 5. 第三方数据集（库文件不入库，脚本本地重建） ----------------------
foreach ($pair in @(
        @{ Name = 'bwiki 图鉴库'; Path = 'datasets\bwiki\bwiki_battle.db'; Size = '≈9.5 MB' },
        @{ Name = 'PvP 数据集'; Path = 'datasets\pvp\pvp_data.db'; Size = '≈5.0 MB' })) {
    $full = Join-Path $Root $pair.Path
    Add-Item -Name $pair.Name -Kind 'dataset' -Ok:(Test-Path $full) `
        -Detail $(if (Test-Path $full) { $pair.Path } else { "缺失 $($pair.Size)" }) `
        -Fix $(if ($pair.Name -like 'bwiki*') {
            'python datasets/tools/bwiki/fetch_bwiki.py; python datasets/tools/bwiki/import_bwiki.py'
        } else {
            'python datasets/tools/pvp/fetch_pvp.py; python datasets/tools/pvp/import_pvp.py'
        }) `
        -Run {
            if ($pair.Name -like 'bwiki*') {
                & $venvPy (Join-Path $Root 'datasets\tools\bwiki\fetch_bwiki.py')
                & $venvPy (Join-Path $Root 'datasets\tools\bwiki\import_bwiki.py')
            } else {
                & $venvPy (Join-Path $Root 'datasets\tools\pvp\fetch_pvp.py')
                & $venvPy (Join-Path $Root 'datasets\tools\pvp\import_pvp.py')
            }
        }
}

# --- 6. 模型权重（可选，只有 -Deep 才提示） -----------------------------
if ($Deep) {
    $models = Join-Path $Root 'datasets\models'
    $hasModels = Test-AnyFile -Path $models -Filter '*.onnx'
    Add-Item -Name '模型权重' -Kind 'dataset' -Ok:$hasModels `
        -Detail '精灵检测/OCR 的可选 onnx；缺了就回退轮廓+模板' `
        -Fix 'python datasets/tools/fetch_upstream.py weights' -Run {
            & $venvPy (Join-Path $Root 'datasets\tools\fetch_upstream.py') weights
        }
}

# --- 输出 ---------------------------------------------------------------
$ready = @($items | Where-Object { $_.ok })
$miss = @($items | Where-Object { -not $_.ok })

if ($Apply) {
    foreach ($item in $miss) {
        if ($item.run) {
            Write-Host ">> 修复 $($item.name)" -ForegroundColor Cyan
            try { & $item.run } catch { Write-Host "  失败: $_" -ForegroundColor Red }
        }
    }
    # 修完重跑一遍体检，让结果反映真实状态
    & $PSCommandPath -Json:$Json -Deep:$Deep
    exit $LASTEXITCODE
}

if ($Json) {
    [pscustomobject]@{
        root    = $Root
        ready   = $ready.Count
        missing = $miss.Count
        items   = $items | Select-Object name, kind, ok, detail, fix
    } | ConvertTo-Json -Depth 4
    exit $(if ($miss.Count -eq 0) { 0 } else { 1 })
}

Write-Host "Rocogi bootstrap -- $Root" -ForegroundColor Cyan
foreach ($item in $items) {
    $tag = if ($item.ok) { '[ ok ]' } else { '[miss]' }
    $color = if ($item.ok) { 'DarkGray' } else { 'Yellow' }
    Write-Host ("{0} {1,-22} {2}" -f $tag, $item.name, $item.detail) -ForegroundColor $color
}
Write-Host ''
if ($miss.Count -eq 0) {
    Write-Host "全部就绪（$($ready.Count) 项）。" -ForegroundColor Green
    exit 0
}
Write-Host "缺 $($miss.Count) 项。逐条修复：" -ForegroundColor Yellow
foreach ($item in $miss) {
    Write-Host ("  - {0}: {1}" -f $item.name, $item.fix) -ForegroundColor DarkYellow
}
Write-Host ''
Write-Host "自动执行能自动的部分： .\scripts\bootstrap.ps1 -Apply" -ForegroundColor Cyan
exit 1
