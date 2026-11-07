# TOOLCHAIN — 便携工具链清单（rocogi/vendor）

> 边界：所有工具链解压到 `work\rocogi\.toolchain\`，只通过**进程内环境变量**使用；
> 不写系统 PATH、不改注册表、不装系统服务（唯一例外：Interception 驱动，见 `BLOCKERS.md` 第 7 项）。
> 所有构建产物、缓存、包仓库也落在 `.toolchain\` 或 `vendor\` 内。

## 1. 复用优先：本机既有组件检查

### 1.1 `C:\Program Files\Bettbox`（另一会话提示，只读检查）

| 项 | 结果 |
|---|---|
| 真实类型 | **Flutter/Dart Windows 桌面应用**（`flutter_windows.dll`、`dartjni.dll`、多个 flutter 插件 dll） |
| 版本 | `1.19.7+2026102201`（文件版本同上） |
| 安装形态 | Inno Setup 安装版：`unins000.exe` / `unins000.dat`，有卸载注册表项 |
| .NET 运行时/SDK | **无**（`dotnet.exe`、`host/fxr`、`shared\Microsoft.NETCore.App`、`sdk` 均不存在） |
| WebView2 | **无**（无 `WebView2Loader.dll`、`Microsoft.Web.WebView2.Core.dll`、`EBWebView`；Flutter 用自己的渲染后端） |
| Node / pnpm / Go / Electron / Qt / OpenCV / Python | 均无 |
| 附带 exe | `Bettbox.exe`、`BettboxCore.exe`、`BettboxHelperService.exe`（应用自身组件，非通用工具链） |
| 是否采用 | **不采用**：不含任何可复用工具链；它也不是 BetterGI 本体（Bettbox 是 Flutter 启动器） |

结论：Bettbox 无法省掉任何需要安装的工具链；BetterGI 仍需 .NET SDK，yotta 仍需 Go/node，WebView2 依赖系统运行时（已满足，见下）。

### 1.2 系统 WebView2 运行时（yotta 直接复用）

- 路径：`C:\Program Files (x86)\Microsoft\EdgeWebView\Application`（版本目录 `156.0.4314.50` / `156.0.4314.58`）
- 注册表版本：`Microsoft Edge WebView2 Runtime 156.0.4314.58`
- 采用：**是**。yotta（Wails v3）运行时直接使用系统 WebView2，不再安装任何 WebView2 包。

### 1.3 `work\.toolchain\` 既有便携组件（跨会话复用，只读使用）

| 组件 | 路径 | 版本 | 用途 | 采用 |
|---|---|---|---|---|
| Python | `work\.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe` | 3.12.16 | 建 venv（爬虫/探测脚本） | 是 |
| Node.js | `work\.toolchain\node\node.exe` | v22.23.4 / npm 10.9.9 | 安装 pnpm、跑 rocokingdom-ui | 是 |
| Git | `work\.toolchain\git\cmd\git.exe` | 2.56.0.windows.4 | pnpm `prepare` 脚本依赖 | 是 |
| GH CLI | `work\.toolchain\gh\bin\gh.exe` | — | 查询 release（未登录，仅匿名） | 是（只读查询） |

## 2. 新增下载（全部官方源）

| 名称 | URL | 版本 | 大小 | SHA-256 | 解压目录 |
|---|---|---|---|---|---|
| Go | `https://go.dev/dl/go1.25.13.windows-amd64.zip` | 1.25.13 | 67,590,465 B | `54A6BBFFADA82938AC4AE66E354B2E9C04EBDCEFF96F8D0455406C723B5ED1FC` | `.toolchain\go` |
| .NET SDK 8 | `https://aka.ms/dotnet/8.0/dotnet-sdk-win-x64.zip` | 8.0.427 | 285,280,040 B | `AB9D4E4275DB9683A6B51640122D184C5C6AE5DA680D0C0ED82E994662353CC8` | `.toolchain\dotnet` |
| .NET SDK 10 | `https://aka.ms/dotnet/10.0/dotnet-sdk-win-x64.zip` | 10.0.403 | 300,745,255 B | `F398979A9CAC2DBA760771C4E01F16E431DCD6BCFB2213E3E8F5B3D354095CC0` | `.toolchain\dotnet10` |
| Node.js | `https://nodejs.org/dist/v24.18.0/node-v24.18.0-win-x64.zip` | 24.18.0 | 37,176,245 B | `0AE68406B42D7725661DA979B1403EC9926DA205C6770827F33AAC9D8F26E821` | `.toolchain\node24\node-v24.18.0-win-x64` |
| pnpm | `npm install -g pnpm@11.5.3`（registry.npmjs.org） | 11.5.3 | — | — | `.toolchain\npm-global` |
| Wails CLI | `go install github.com/wailsapp/wails/v3/cmd/wails3@v3.0.0-beta.6` | v3.0.0-beta.6 | 52.7 MB | — | `.toolchain\gobin\wails3.exe` |
| Interception | `https://github.com/oblitum/Interception/releases/download/v1.0.1/Interception.zip` | v1.0.1 | 389,119 B | `AD038963D6413055765128B0B931F6E765147C9916DBA79E65D872B261F9AF10` | `.toolchain\interception\Interception` |
| rocom-pets（渲染器） | `https://github.com/whoisnian/rocom-pets/releases/download/1.14.2/rocom-pets-1.14.2-windows-x64.exe` | 1.14.2 | 54,496,847 B | `21DAFC7ED88036BA8C400DD58B8E971D1653333B011786E9E0BC0271D178B4E5` | `.toolchain\rocom-pets` |

> 说明：`dotnet-sdk-8.0` 下载后实测 BetterGI 目标框架是 `net10.0-windows10.0.22621.0`，
> 故又补了 .NET 10 SDK；8.0 SDK 保留（不删除），供其它 .NET 8 项目使用。

## 3. 进程内使用模板

```powershell
# Go + Wails
$tc = "c:\Users\13005\Downloads\work\rocogi\.toolchain"
$env:PATH        = "$tc\gobin;$tc\go\bin;$env:PATH"
$env:GOROOT      = "$tc\go"
$env:GOPATH      = "$tc\gopath"
$env:GOCACHE     = "$tc\gocache"
$env:GOTOOLCHAIN = "local"

# .NET 10（BetterGI）
$env:DOTNET_ROOT   = "$tc\dotnet10"
$env:PATH          = "$tc\dotnet10;$env:PATH"
$env:NUGET_PACKAGES= "$tc\nuget-packages"
$env:APPDATA       = "$tc\appdata"      # 避免读取/写入用户级 NuGet.Config（沙箱下会被拒）
$env:DOTNET_CLI_HOME = "$tc\dotnet-home"

# Node 24 + pnpm（yotta / rocokingdom-ui）
$env:PATH       = "$tc\node24\node-v24.18.0-win-x64;$tc\npm-global;c:\Users\13005\Downloads\work\.toolchain\git\cmd;$env:PATH"
$env:PNPM_HOME  = "$tc\pnpm-home"
$env:npm_config_cache = "$tc\npm-cache"
```

## 4. 体积（`.toolchain\` 下新增/相关目录）

| 目录 | 体积 |
|---|---|
| `go` | 199.6 MB |
| `gopath`（Go module cache + sumdb） | 919.6 MB |
| `gocache` | 319.1 MB |
| `gobin`（wails3.exe） | 50.3 MB |
| `dotnet`（SDK 8.0.427） | 714.2 MB |
| `dotnet10`（SDK 10.0.403） | 770.2 MB |
| `nuget-packages`（BetterGI 依赖缓存） | 3531.4 MB |
| `node24` | 100.8 MB |
| `npm-global`（pnpm 11.5.3） | 17.7 MB |
| `pnpm-store` + `pnpm-home` | 1939.5 MB + 33.2 MB |
| `rocom-pets`（含 1.14.2 exe 与探测产物） | 52 MB |
| `interception`（驱动安装包 + samples） | 0.8 MB |
| `venv-crawler`（requests/bs4/lxml/Pillow/imageio-ffmpeg/pyinstxtractor-ng） | 149.5 MB |
| ~~`service.exe_extracted`~~（已清理，sift 黑盒提取中间产物） | -158.5 MB |
| ~~`downloads`~~（已清理，原始 zip；URL/sha256 见上表留档） | -776.7 MB |

> **已清理项（2026-11-05）**：删除 `.toolchain\downloads`（776.7 MB，7 个 zip）与 `.toolchain\service.exe_extracted`（158.5 MB，535 个文件），共释放 **935.2 MB**。`probe_service.py` 只依赖 `vendor\sift-map-tracker\sift-map-tracker\service\service.exe`，不需要解包副本；重建必需的 `nuget-packages` / `pnpm-store` / `gopath` / `gocache` 全部保留。

> 另有既有 `python`(61.4 MB)、`git`(91.8 MB)、`node`(94.5 MB)、`gh`(39.9 MB)、`uv`(31 MB)、
> `cmake`(136.7 MB)、`w64devkit`(716.7 MB)，非本次新增。

## 5. 已知限制与规避

1. **Windows 未开开发者模式**：`pnpm` 在 `store\v11\projects\<hash> -> 项目目录` 处创建符号链接会
   `EBUSY/EPERM`。规避：`--node-linker=hoisted --config.package-import-method=copy`，并直接调用
   `node_modules\.bin\run-s` / `vp`，绕过 `pnpm run` 的隐式 install 检查。
2. **沙箱拒绝读取 `%APPDATA%\NuGet\NuGet.Config`**：构建时把进程内 `APPDATA` 指到
   `.toolchain\appdata`，NuGet 只读该目录（为空则使用默认源）。
3. **yotta `frontend` 声明 `engines.node>=24` 且 `engine-strict=true`**：必须用 Node 24（v22 会拒绝安装）。
4. **yotta 前端依赖 Wails 生成的 `frontend/bindings/`**（gitignore）：必须先
   `node frontend/scripts/generate-bindings.mjs`（内部调用 `wails3 generate bindings -ts ./...`），否则
   `build:app` 报 `Event bindings module not found`。
5. **pnpm 由 `packageManager` 字段锁定 11.1.2**（yotta）：会被 corepack 自动下载到
   `pnpm-home\store\v11\links`；不影响离线复用，已缓存。
