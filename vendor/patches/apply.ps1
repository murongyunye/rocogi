# vendor/patches/apply.ps1
# 用法：.\apply.ps1 -Repo Makapic-RocoPilot -Diff .\Makapic-RocoPilot\0001-path-fix.diff
# 仅作用于 vendor/<repo>，绝不触碰 work/upstream。

param(
    [Parameter(Mandatory = $true)][string]$Repo,
    [Parameter(Mandatory = $true)][string]$Diff,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$vendorRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoPath = Join-Path $vendorRoot $Repo
$diffPath = Resolve-Path $Diff

if (-not (Test-Path $repoPath)) {
    throw "vendor 内不存在仓库: $repoPath"
}
if (-not $repoPath.StartsWith($vendorRoot)) {
    throw "拒绝越界: $repoPath"
}

$git = Join-Path (Split-Path -Parent (Split-Path -Parent $vendorRoot)) '.toolchain\git\cmd\git.exe'
if (-not (Test-Path $git)) {
    throw "未找到便携 git: $git"
}

$args = @('-C', $repoPath, 'apply', '--whitespace=nowarn')
if ($Check) { $args += '--check' }
$args += $diffPath.Path

& $git @args
if ($LASTEXITCODE -ne 0) {
    throw "补丁应用失败 (exit=$LASTEXITCODE): $diffPath"
}

Write-Host ("补丁已应用到 vendor/{0}: {1}" -f $Repo, (Split-Path -Leaf $diffPath))
Write-Host "请同步在 vendor/docs/IMPORT_REPORT.md 登记该补丁。"
