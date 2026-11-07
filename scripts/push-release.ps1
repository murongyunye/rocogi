<#
.SYNOPSIS
    把当前 commit 推到 GitHub main，并发布 v<VERSION> release（附 lite 包、C 核心包与校验和）。

.DESCRIPTION
    只在需要时读令牌，令牌不落盘、不写入 git remote：
      $env:GH_TOKEN = "ghp_xxx"      # 或 GITHUB_TOKEN
      .\scripts\push-release.ps1

    令牌权限：classic 勾 repo；fine-grained 给 Contents: Read and write + Releases。
    推送用一次性的 https://<token>@... 地址，结束后 remote 仍是无凭据的 origin。

.PARAMETER Repo
    owner/name，默认 murongyunyeh/rocogi。

.PARAMETER SkipPush
    只建 release（commit 已经在远端时用）。

.PARAMETER SkipRelease
    只推 commit（不要建 release 时用）。
#>
[CmdletBinding()]
param(
    [string]$Repo = "murongyunyeh/rocogi",
    [switch]$SkipPush,
    [switch]$SkipRelease
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $version = (Get-Content (Join-Path $root 'VERSION') -Raw).Trim()
    $tag = "v$version"

    # git：优先 PATH，其次仓库旁的便携 MinGit（本机没装 git 时用）
    $git = (Get-Command git.exe -ErrorAction SilentlyContinue).Source
    if (-not $git) {
        $candidate = Join-Path (Split-Path -Parent $root) '.tmp\gitkit\mingit\cmd\git.exe'
        if (Test-Path $candidate) { $git = $candidate }
    }
    if (-not $git) { throw "找不到 git.exe：装 Git 或把它放到 <work>\.tmp\gitkit\mingit\cmd\git.exe" }
    $sha = & $git -c core.quotepath=false rev-parse HEAD
    Write-Host "repo    : $Repo"
    Write-Host "version : $version ($tag)"
    Write-Host "commit  : $sha"

    if (-not $SkipPush) {
        $token = $env:GH_TOKEN
        if (-not $token) { $token = $env:GITHUB_TOKEN }
        if (-not $token) { throw '缺少令牌：先设置 $env:GH_TOKEN（不要提交到仓库）' }
        $pushUrl = "https://x-access-token:$token@github.com/$Repo.git"
        Write-Host '==> git push HEAD:main'
        & $git -c core.quotepath=false -C $root push --porcelain $pushUrl "HEAD:main"
        if ($LASTEXITCODE -ne 0) { throw "push 失败（exit $LASTEXITCODE）" }
    }

    if (-not $SkipRelease) {
        $token = $env:GH_TOKEN
        if (-not $token) { $token = $env:GITHUB_TOKEN }
        if (-not $token) { throw '缺少令牌：先设置 $env:GH_TOKEN' }
        $headers = @{
            Authorization          = "Bearer $token"
            Accept                 = 'application/vnd.github+json'
            'X-GitHub-Api-Version' = '2022-11-28'
            'User-Agent'           = 'rocogi-release-script'
        }

        # release notes 取 CHANGELOG 里 "## <version>" 到下一个 "## " 之间
        $notes = "Rocogi $version"
        $changelog = Join-Path $root 'CHANGELOG.md'
        if (Test-Path $changelog) {
            # 必须显式 -Encoding UTF8：Windows PowerShell 5.1 默认按 ANSI(GBK) 读，
            # 中文 release notes 会变成乱码再以 UTF-8 提交到 GitHub。
            $lines = Get-Content $changelog -Encoding UTF8
            $start = -1
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match "^##\s+$([regex]::Escape($version))\b") { $start = $i; break }
            }
            if ($start -ge 0) {
                $body = New-Object System.Collections.Generic.List[string]
                for ($i = $start + 1; $i -lt $lines.Count; $i++) {
                    if ($lines[$i] -match '^##\s') { break }
                    $body.Add($lines[$i])
                }
                $text = ($body -join "`n").Trim()
                if ($text) { $notes = $text }
            }
        }

        $existing = $null
        try {
            $existing = Invoke-RestMethod -Method Get -Headers $headers `
                -Uri "https://api.github.com/repos/$Repo/releases/tags/$tag"
        } catch {
            $existing = $null
        }

        if ($existing) {
            Write-Host "release $tag 已存在：$($existing.html_url)（跳过创建）"
            $release = $existing
        } else {
            Write-Host "==> 创建 release $tag"
            $payload = @{
                tag_name         = $tag
                target_commitish = $sha.Trim()
                name             = "Rocogi $version"
                body             = $notes
                draft            = $false
                prerelease       = $false
            } | ConvertTo-Json -Depth 4
            $release = Invoke-RestMethod -Method Post -Headers $headers `
                -Uri "https://api.github.com/repos/$Repo/releases" `
                -ContentType 'application/json; charset=utf-8' `
                -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
            Write-Host "created: $($release.html_url)"
        }

        $assets = @(
            (Join-Path $root "release\rocogi-$version-lite.zip"),
            (Join-Path $root 'backend-c\rocogi-core-0.2.0.zip'),
            (Join-Path $root "release\checksums-$tag.txt")
        ) | Where-Object { Test-Path $_ }

        if (-not $assets) { throw '没有找到可上传的发行物（先跑 scripts\package-release.py --mode lite）' }

        $uploaded = @{}
        foreach ($path in $assets) {
            $name = Split-Path $path -Leaf
            $sizeMb = [math]::Round((Get-Item $path).Length / 1MB, 1)
            $already = ($release.assets | Where-Object { $_.name -eq $name })
            if ($already) {
                Write-Host "asset 已存在，跳过：$name"
                $uploaded[$name] = $already.browser_download_url
                continue
            }
            Write-Host "==> 上传 $name ($sizeMb MB)"
            $url = "https://uploads.github.com/repos/$Repo/releases/$($release.id)/assets?name=$([uri]::EscapeDataString($name))"
            $asset = Invoke-RestMethod -Method Post -Headers $headers `
                -Uri $url -ContentType 'application/octet-stream' -InFile $path
            $uploaded[$name] = $asset.browser_download_url
        }

        Write-Host ''
        Write-Host "release : $($release.html_url)"
        foreach ($k in $uploaded.Keys) { Write-Host "  $k -> $($uploaded[$k])" }
    }
} finally {
    Pop-Location
}
