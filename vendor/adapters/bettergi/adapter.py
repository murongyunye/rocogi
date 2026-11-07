"""BetterGI（C#）契约导出层：截图/热键/输入三个子项目的公开类型清单。

不构建、不运行（本机 dotnet 异常），只把可复用的接口契约导出为 JSON。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import repo_dir, run  # noqa: E402

PROJECTS = ["Fischless.GameCapture", "Fischless.HotkeyCapture", "Fischless.WindowsInput"]


def _public_types(folder: Path) -> list[str]:
    pattern = re.compile(r"public\s+(?:sealed\s+|abstract\s+|static\s+|partial\s+)*(class|interface|record|enum)\s+(\w+)")
    found: list[str] = []
    for file in folder.rglob("*.cs"):
        text = file.read_text(encoding="utf-8", errors="ignore")
        for kind, name in pattern.findall(text):
            found.append(f"{kind}:{name}")
    return sorted(set(found))


def body(result) -> None:
    repo = repo_dir("babalae-better-genshin-impact")
    result.add("repo", True, repo.name)

    inventory = {}
    for project in PROJECTS:
        folder = repo / project
        types = _public_types(folder)
        inventory[project] = types
        result.add(project, folder.is_dir() and bool(types), f"{len(types)} 个公开类型")

    main_cs = sorted(p.name for p in (repo / "BetterGenshinImpact").rglob("*.cs"))
    viewmodels = sorted(p.name for p in (repo / "BetterGenshinImpact" / "ViewModel").rglob("*.cs")) if (repo / "BetterGenshinImpact" / "ViewModel").exists() else []
    result.add("main_project", len(main_cs) > 100, f"{len(main_cs)} 个 .cs")
    result.add("viewmodels", bool(viewmodels), f"{len(viewmodels)} 个 ViewModel 文件")

    solution = repo / "BetterGenshinImpact.sln"
    result.add("solution", solution.is_file(), solution.name)

    result.contract.update(
        {
            "language": "C# / .NET 8 / WPF",
            "projects": PROJECTS,
            "public_types": inventory,
            "entry_project": "BetterGenshinImpact.sln",
            "reusable_contracts": {
                "capture": "Fischless.GameCapture 的 BitBlt / WGC / SharedSurface 抓帧",
                "hotkey": "Fischless.HotkeyCapture 的 RegisterHotKey 封装",
                "input": "Fischless.WindowsInput 的 SendInput 封装",
            },
            "build_requirements": [".NET 8 SDK", "NuGet 联网还原", "Windows 10/11 + WPF"],
            "license": "GPL-3.0",
            "minimal_run_plan": "不静态链接；以独立进程/独立可执行复用其截图与输入契约，避免 GPL 传染",
        }
    )
    result.block("构建需 .NET 8 SDK + NuGet；本机仅有异常 dotnet，未执行构建，只导出契约")


if __name__ == "__main__":
    raise SystemExit(run("bettergi", "babalae-better-genshin-impact", body))
