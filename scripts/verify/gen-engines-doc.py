"""Generate docs/engines.md from the live backend (mock target must be reachable).

Run from the repository root with the backend up:
    .\\.venv\\Scripts\\python.exe scripts/verify/gen-engines-doc.py

数据源是 backend/app/components.py 的组元注册表（/api/components）与引擎预设（/api/engines），
所以改了组元后重跑本脚本，文档自动跟上，不需要手改表格。
"""
import json
import pathlib
import urllib.request

BASE = "http://127.0.0.1:8787"
ROOT = pathlib.Path(__file__).resolve().parents[2]


def fetch(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    comp = fetch("/api/components")
    engines = fetch("/api/engines")
    stats = comp["stats"]

    out = []
    w = out.append

    w("# 引擎分组、动作与完善度")
    w("")
    w("> 本文由 `scripts/verify/gen-engines-doc.py` 依据 `/api/components`、`/api/engines` 生成，")
    w("> 数据源是 `backend/app/components.py` 的组元注册表，不是手写清单。改完组元重跑脚本即可刷新。")
    w("")
    w("## 总览")
    w("")
    w(f"- 引擎 **{stats['engineCount']}** 个、组元 **{stats['componentCount']}** 个、功能 **{stats['featureCount']}** 个")
    w(f"- 功能→组元绑定 **{stats['bindingCount']}** 条；被复用的组元 **{stats['reusableComponents']}**/{stats['componentCount']}"
      f"（最高复用 {stats['maxReuse']} 个功能，单功能专用 {stats['singleUseComponents']} 个）")
    w(f"- 完善度：ready **{stats['readyComponents']}** / partial **{stats['partialComponents']}** / 能力缺口 **{stats['gapCount']}**")
    w(f"- 平均每个功能装配 {stats['avgComponentsPerFeature']} 个组元、{stats['avgEnginesPerFeature']} 个引擎")
    w("")
    w("分组原则：引擎只取「组元」，组元只做一件事；同一能力可被多个功能复用，不在功能里重复实现。")
    w("")

    w("## 引擎")
    w("")
    w("| 引擎 | 名称 | 组元 | ready / partial | 说明 |")
    w("| --- | --- | --- | --- | --- |")
    for e in comp["engines"]:
        comps = e["components"]
        ready = sum(1 for c in comps if c["status"] == "ready")
        partial = sum(1 for c in comps if c["status"] == "partial")
        w(f"| `{e['id']}` | {e['name']} | {len(comps)} | {ready} / {partial} | {e['summary']} |")
    w("")

    w("## 执行组")
    w("")
    w("| 组 | 执行入口 | 引擎 | 动作 | 组元 |")
    w("| --- | --- | --- | --- | --- |")
    for g in comp["groups"]:
        w(f"| {g['name']} (`{g['id']}`) | `{g['exe']}` | {', '.join('`' + x + '`' for x in g['engines'])} | "
          f"{', '.join('`' + a + '`' for a in g['actions'])} | {g['componentCount']}（ready {g['readyCount']}） |")
    w("")

    w("## 组元明细")
    w("")
    for e in comp["engines"]:
        w(f"### {e['name']}（`{e['id']}`）")
        w("")
        w(e["summary"])
        w("")
        w("| 组元 | 说明 | 实现 | 状态 | 复用 |")
        w("| --- | --- | --- | --- | --- |")
        for c in e["components"]:
            status = c["status"]
            note = f"{status}（{c['statusNote']}）" if c.get("statusNote") else status
            w(f"| `{c['id']}` | {c['name']} — {c['detail']} | `{c['code']}` | {note} | {c['reuse']} 功能 |")
        w("")

    w("## 功能装配")
    w("")
    w("| 功能 | 路由 | 组元数 | 组元 |")
    w("| --- | --- | --- | --- |")
    for f in comp["features"]:
        w(f"| {f['name']} (`{f['id']}`) | `{f['route']}` | {len(f['components'])} | "
          f"{' '.join('`' + c + '`' for c in f['components'])} |")
    w("")

    partials = [c for e in comp["engines"] for c in e["components"] if c["status"] == "partial"]
    w("## partial 组元与原因")
    w("")
    w("partial 表示「契约已接、能力受外部环境限制」，在组件图谱里如实标注，mock 目标下不影响主链路。")
    w("")
    w("| 组元 | 原因 |")
    w("| --- | --- |")
    for c in partials:
        w(f"| `{c['id']}` | {c.get('statusNote') or '-'} |")
    w("")

    w("## 引擎参数预设")
    w("")
    w(f"当前生效：`{engines.get('applied')}`")
    w("")
    w("| 预设 | 名称 | 目标 | 输入 | 定位源 | 标签 |")
    w("| --- | --- | --- | --- | --- | --- |")
    for p in engines["presets"]:
        s = p["settings"]
        w(f"| `{p['id']}` | {p['name']} | {s['target']['kind']} | {s['input']['backend']} | "
          f"{s['map']['position_source']} | {p.get('tag', '-')} |")
    w("")
    w("预设只写引擎参数；窗口标题、输入后端、定位源这类本机信息在「设置」里保存，工作流只带 `targetSlot`。")
    w("")

    target = ROOT / "docs" / "engines.md"
    target.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {target} ({len(out)} lines)")


if __name__ == "__main__":
    main()
