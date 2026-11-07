<#!
.SYNOPSIS
    重启后自检：Interception 驱动 / interception_create_context() / 端口 / 便携工具链版本。

.DESCRIPTION
    只读检查，不修改系统、不安装任何组件、**不会重启系统**。
    输出 PASS/FAIL 表；有 FAIL 不影响退出码（退出码固定 0，便于重复跑）。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File rocogi\vendor\tools\post-reboot-check.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'SilentlyContinue'
$root  = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\work\rocogi
$work  = Split-Path -Parent $root                                # ...\work
$tc    = Join-Path $root '.toolchain'
$vendor = Join-Path $root 'vendor'

$checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
    param(
        [string]$Area,
        [string]$Item,
        [bool]$Pass,
        [string]$Detail
    )
    $checks.Add([pscustomobject]@{
        Area   = $Area
        Item   = $Item
        Result = if ($Pass) { 'PASS' } else { 'FAIL' }
        Detail = $Detail
    })
}

# ---------------------------------------------------------------- 1. Interception
$kbdGuid = '{4D36E96B-E325-11CE-BFC1-08002BE10318}'
$mouseGuid = '{4D36E96F-E325-11CE-BFC1-08002BE10318}'

foreach ($cls in @(
        @{ Name = 'keyboard'; Guid = $kbdGuid; Expect = 'keyboard' },
        @{ Name = 'mouse';    Guid = $mouseGuid; Expect = 'mouse' })) {

    $key = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\$($cls.Guid)"
    $upper = @()
    $upper = @((Get-ItemProperty -Path $key -Name UpperFilters).UpperFilters)
    $hasFilter = $upper -contains $cls.Expect
    Add-Check 'Interception' "$($cls.Name) UpperFilters" $hasFilter ("当前: " + ($(if ($upper.Count) { $upper -join ',' } else { '<空>' })))

    $sys = "C:\Windows\System32\drivers\$($cls.Name).sys"
    Add-Check 'Interception' "$($cls.Name).sys 文件" (Test-Path -LiteralPath $sys) $(if (Test-Path -LiteralPath $sys) { $sys } else { '缺失' })

    $drv = Get-CimInstance Win32_SystemDriver -Filter "Name='$($cls.Name)'" -ErrorAction SilentlyContinue
    Add-Check 'Interception' "$($cls.Name) 驱动状态" ($drv -and $drv.State -eq 'Running') ("State=" + $(if ($drv) { $drv.State } else { 'NotPresent' }))
}

# interception_create_context()
$dll = Join-Path $vendor 'SCH-CMYK-game-automation\interception.dll'
if (-not (Test-Path -LiteralPath $dll)) {
    Add-Check 'Interception' 'interception_create_context()' $false "找不到 interception.dll: $dll"
} else {
    try {
        $escaped = $dll.Replace('\', '\\')
        $code = @'
using System;
using System.Runtime.InteropServices;
public static class InterceptionProbe {
    [DllImport("__DLL__", CallingConvention = CallingConvention.Cdecl, SetLastError = true)]
    public static extern IntPtr interception_create_context();
    [DllImport("__DLL__", CallingConvention = CallingConvention.Cdecl)]
    public static extern void interception_destroy_context(IntPtr context);
}
'@
        $code = $code.Replace('__DLL__', $escaped)
        Add-Type -TypeDefinition $code -Language CSharp -ErrorAction Stop
        $ctx = [InterceptionProbe]::interception_create_context()
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($ctx -ne [IntPtr]::Zero) {
            [InterceptionProbe]::interception_destroy_context($ctx)
            Add-Check 'Interception' 'interception_create_context()' $true "返回非空 context，已 destroy；dll=$dll"
        } else {
            Add-Check 'Interception' 'interception_create_context()' $false "返回 NULL，Win32Error=$err（驱动未运行/未重启最常见）"
        }
    } catch {
        $msg = $_.Exception.Message
        Add-Check 'Interception' 'interception_create_context()' $false "DLL 加载/调用失败：$msg"
    }
}

# ---------------------------------------------------------------- 2. 端口
foreach ($port in 8787, 8788, 5173, 8800) {
    $client = New-Object System.Net.Sockets.TcpClient
    $ok = $false
    try {
        $ar = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if ($ar.AsyncWaitHandle.WaitOne(300, $false)) {
            $client.EndConnect($ar)
            $ok = $true
        }
    } catch {
        $ok = $false
    } finally {
        $client.Close()
    }
    $listen = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    $detail = if ($ok) { 'TCP 可连接' } elseif ($listen) { '端口在监听但连接失败' } else { '未监听（服务未启动）' }
    Add-Check 'Ports' "$port" $ok $detail
}

# ---------------------------------------------------------------- 3. 工具链版本
function Get-VersionLine {
    param([string]$Exe, [string[]]$Arguments)
    if (-not (Test-Path -LiteralPath $Exe)) { return @{ Ok = $false; Text = '路径不存在' } }
    try {
        $out = & $Exe @Arguments 2>$null
        $text = (@($out) -join ' ').Trim()
        if (-not $text) { return @{ Ok = $false; Text = '无输出' } }
        return @{ Ok = $true; Text = $text }
    } catch {
        return @{ Ok = $false; Text = $_.Exception.Message }
    }
}

# 版本检查使用进程内环境变量，不写系统 PATH
$oldPath = $env:PATH
$env:GOROOT = Join-Path $tc 'go'
$env:GOPATH = Join-Path $tc 'gopath'
$env:GOCACHE = Join-Path $tc 'gocache'
$env:DOTNET_ROOT = Join-Path $tc 'dotnet10'
$env:PATH = (@(
    (Join-Path $tc 'go\bin'),
    (Join-Path $tc 'gobin'),
    (Join-Path $tc 'node24\node-v24.18.0-win-x64'),
    (Join-Path $tc 'npm-global'),
    $env:PATH
) -join ';')

$tools = @(
    @{ Name = 'Go';      Exe = (Join-Path $tc 'go\bin\go.exe');            Arguments = @('version') },
    @{ Name = 'Node 24'; Exe = (Join-Path $tc 'node24\node-v24.18.0-win-x64\node.exe'); Arguments = @('--version') },
    @{ Name = 'Node 22'; Exe = (Join-Path $work '.toolchain\node\node.exe'); Arguments = @('--version') },
    @{ Name = 'dotnet8'; Exe = (Join-Path $tc 'dotnet\dotnet.exe');        Arguments = @('--version') },
    @{ Name = 'dotnet10';Exe = (Join-Path $tc 'dotnet10\dotnet.exe');      Arguments = @('--version') },
    @{ Name = 'Python';  Exe = (Join-Path $work '.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe'); Arguments = @('--version') },
    @{ Name = 'Git';     Exe = (Join-Path $work '.toolchain\git\cmd\git.exe'); Arguments = @('--version') }
)
foreach ($t in $tools) {
    $r = Get-VersionLine -Exe $t.Exe -Arguments $t.Arguments
    Add-Check 'Toolchain' $t.Name $r.Ok $r.Text
}

# wails3 没有 --version；从 Go 模块信息读取
$wailsExe = Join-Path $tc 'gobin\wails3.exe'
if (Test-Path -LiteralPath $wailsExe) {
    $modLine = (& (Join-Path $tc 'go\bin\go.exe') version -m $wailsExe 2>$null | Select-String 'mod\s+github\.com/wailsapp/wails').Line
    Add-Check 'Toolchain' 'Wails3' ([bool]$modLine) $(if ($modLine) { $modLine.Trim() } else { "$wailsExe（无法读取模块版本）" })
} else {
    Add-Check 'Toolchain' 'Wails3' $false '缺失'
}

# pnpm.cmd 会输出帮助头部，单独取版本行
$pnpmExe = Join-Path $tc 'npm-global\pnpm.cmd'
if (Test-Path -LiteralPath $pnpmExe) {
    $pv = (& $pnpmExe --version 2>$null | Out-String).Trim()
    Add-Check 'Toolchain' 'pnpm' ([bool]$pv) $pv
} else {
    Add-Check 'Toolchain' 'pnpm' $false '缺失'
}
$env:PATH = $oldPath

$rocom = Join-Path $tc 'rocom-pets\rocom-pets-1.14.2-windows-x64.exe'
Add-Check 'Toolchain' 'rocom-pets 1.14.2' (Test-Path -LiteralPath $rocom) $(if (Test-Path -LiteralPath $rocom) { $rocom } else { '缺失' })

# 构建产物
Add-Check 'Artifacts' 'yotta.exe' (Test-Path -LiteralPath (Join-Path $tc 'build\yotta.exe')) $(Join-Path $tc 'build\yotta.exe')
$bg = Join-Path $vendor 'babalae-better-genshin-impact\BetterGenshinImpact\bin\Release'
Add-Check 'Artifacts' 'BetterGI Release 产物' (Test-Path -LiteralPath $bg) $bg

# ---------------------------------------------------------------- 输出
$checks | Format-Table -AutoSize -Property Area, Item, Result, Detail | Out-String -Width 220 | Write-Host

$pass = ($checks | Where-Object Result -eq 'PASS').Count
$fail = ($checks | Where-Object Result -eq 'FAIL').Count
Write-Host ("汇总: PASS={0}  FAIL={1}  (本脚本不会重启系统；FAIL 项见上表 Detail)" -f $pass, $fail)

if ($checks | Where-Object { $_.Area -eq 'Interception' -and $_.Item -eq 'interception_create_context()' -and $_.Result -eq 'FAIL' }) {
    Write-Host '提示: 若刚完成驱动安装，请先手动重启一次，再运行本脚本。'
}
exit 0
