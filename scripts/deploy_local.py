from __future__ import annotations

"""One-command local deployment and verification for Rocogi.

Run from the repository (or from anywhere with --root):

    python scripts/deploy_local.py --root C:\\Users\\13005\\Downloads\\rocogi

The script prepares the venv, installs dependencies, builds the frontend,
optionally builds Windows engines, downloads the optional SIFT package,
starts the local service and verifies the main API surfaces. All generated
files stay under --root (venv, caches, runtime, dist, optional).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

IS_WIN = os.name == "nt"
DEFAULT_ROOT = r"C:\Users\13005\Downloads\rocogi" if IS_WIN else str(Path(__file__).resolve().parents[1])
DEFAULT_REPO = "murongyunyeh/rocogi"
DEFAULT_TAG = "v0.2.0"


class DeployError(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"\n[deploy] {message}", flush=True)


def run(
    command: List[str],
    cwd: Path,
    env: Dict[str, str],
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    print("[run] " + " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
    )
    if check and result.returncode != 0:
        detail = (result.stdout or "") + (result.stderr or "")
        raise DeployError(
            f"命令失败（退出码 {result.returncode}）: {' '.join(str(part) for part in command)}\n{detail[-2000:]}"
        )
    return result


def require(name: str) -> None:
    if not shutil.which(name):
        raise DeployError(f"缺少命令: {name}，请先安装并加入 PATH")


def venv_python(root: Path) -> Path:
    return root / (".venv/Scripts/python.exe" if IS_WIN else ".venv/bin/python")


def ensure_repo(root: Path, repo: str, no_pull: bool) -> None:
    if (root / ".git").exists():
        if not no_pull:
            log("更新仓库")
            env = os.environ.copy()
            pull = run(["git", "-C", str(root), "pull", "--ff-only"], cwd=root, env=env, check=False)
            if pull.returncode != 0:
                if shutil.which("gh"):
                    log("配置 GitHub 凭据后重试")
                    run(["gh", "auth", "setup-git"], cwd=root, env=env)
                    pull = run(["git", "-C", str(root), "pull", "--ff-only"], cwd=root, env=env, check=False)
                if pull.returncode != 0:
                    raise DeployError(
                        "git pull 失败。请先执行 gh auth login 或使用 --no-pull 跳过更新。\n"
                        + ((pull.stdout or "") + (pull.stderr or ""))[-1000:]
                    )
        return
    if root.exists() and any(root.iterdir()):
        raise DeployError(f"目录非空且不是 Git 仓库: {root}，请先清理或换目录")
    root.mkdir(parents=True, exist_ok=True)
    log("克隆私有仓库")
    require("gh")
    run(["gh", "repo", "clone", repo, str(root)], cwd=root.parent, env=os.environ.copy())


def build_env(root: Path) -> Dict[str, str]:
    cache = root / ".cache"
    tmp = cache / "tmp"
    for path in (cache / "pip", cache / "npm", cache / "pyinstaller", tmp):
        path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "PIP_CACHE_DIR": str(cache / "pip"),
            "npm_config_cache": str(cache / "npm"),
            "PYINSTALLER_CONFIG_DIR": str(cache / "pyinstaller"),
            "TMP": str(tmp),
            "TEMP": str(tmp),
            "PYTHONPATH": str(root / "backend"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
    )
    return env


def ensure_dependencies(root: Path, env: Dict[str, str], skip: bool) -> Path:
    python = venv_python(root)
    if not python.exists():
        log("创建虚拟环境")
        run([sys.executable, "-m", "venv", str(root / ".venv")], cwd=root, env=env)
        python = venv_python(root)
    if not python.exists():
        raise DeployError(f"虚拟环境创建失败: {python}")
    if skip:
        return python
    log("安装后端依赖")
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=root, env=env)
    run(
        [str(python), "-m", "pip", "install", "-r", str(root / "backend/requirements.txt"), "pytest"],
        cwd=root,
        env=env,
    )
    return python


def npm(args: List[str], cwd: Path, env: Dict[str, str]) -> None:
    command = ["cmd", "/c", "npm", *args] if IS_WIN else ["npm", *args]
    run(command, cwd=cwd, env=env)


def ensure_frontend(root: Path, env: Dict[str, str], force: bool, skip: bool) -> None:
    index = root / "frontend/dist/index.html"
    if skip and not index.exists():
        raise DeployError("前端未构建，不能跳过")
    if index.exists() and not force:
        return
    log("安装并构建前端")
    require("npm")
    npm(["install", "--no-audit", "--no-fund"], root / "frontend", env)
    npm(["run", "build"], root / "frontend", env)
    if not index.exists():
        raise DeployError("前端构建后仍缺少 frontend/dist/index.html")


def run_tests(root: Path, python: Path, env: Dict[str, str], skip: bool) -> None:
    if skip:
        return
    log("运行后端测试")
    run([str(python), "-m", "pytest", "-q", "backend/tests"], cwd=root, env=env)


def engine_path(root: Path, name: str) -> Path:
    suffix = ".exe" if IS_WIN else ""
    return root / "dist/engines" / f"{name}{suffix}"


def parse_engine_json(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise DeployError(f"引擎未返回 JSON: {text[-500:]}")
    data = json.loads(text[start : end + 1])
    if not data.get("ok"):
        raise DeployError(f"引擎返回失败: {data.get('error') or data}")
    return data.get("result") or {}


def engine_call(exe: Path, args: List[str], root: Path, env: Dict[str, str]) -> Dict[str, Any]:
    result = run([str(exe), *args], cwd=root, env=env, capture=True)
    return parse_engine_json(result.stdout)


def build_engines(root: Path, env: Dict[str, str], requested: bool, skip: bool) -> bool:
    if skip:
        return False
    if not IS_WIN and not requested:
        print("[deploy] 非 Windows 环境默认跳过引擎构建，使用 --build-engines 可强制执行")
        return False
    log("构建 headless 引擎")
    if IS_WIN:
        require("powershell")
        run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(root / "scripts/build-engines.ps1"),
            ],
            cwd=root,
            env=env,
        )
    else:
        run(["bash", str(root / "scripts/build-engines.sh")], cwd=root, env=env)
    missing = [name for name in ("RocogiSense", "RocogiInput", "RocogiSift", "RocogiBattle", "RocogiFlow", "RocogiEngine") if not engine_path(root, name).exists()]
    if missing:
        raise DeployError(f"引擎构建后缺少: {', '.join(missing)}")
    return True


def verify_engines(root: Path, env: Dict[str, str]) -> Dict[str, Any]:
    log("冒烟测试引擎")
    checks = [
        ("RocogiSense", ["--action", "templates"]),
        ("RocogiSense", ["--action", "sprites"]),
        ("RocogiSense", ["--action", "ocr", "--params", '{"roi":[0.03,0.86,0.25,0.06]}']),
        ("RocogiSense", ["--action", "foreground"]),
        ("RocogiInput", ["--action", "press", "--params", '{"key":"x"}']),
        ("RocogiInput", ["--action", "hotkey"]),
        ("RocogiSift", ["--action", "route", "--params", '{"labels":["宝箱"],"limit":2}']),
        ("RocogiSift", ["--action", "tracker_info"]),
        ("RocogiBattle", ["--action", "dex_detail", "--params", '{"name":"迪莫"}']),
        ("RocogiBattle", ["--action", "analyze", "--params", '{"team":["迪莫","喵喵"]}']),
        ("RocogiBattle", ["--action", "turn_state"]),
        ("RocogiFlow", ["--action", "workflows"]),
        ("RocogiEngine", ["--action", "library"]),
        ("RocogiEngine", ["--action", "sense.templates"]),
        ("RocogiEngine", ["--action", "sense.sprites"]),
        ("RocogiEngine", ["--action", "battle.turn_state"]),
        ("RocogiEngine", ["--action", "battle.analyze", "--params", '{"team":["迪莫","喵喵"]}']),
    ]
    results = []
    for name, args in checks:
        engine_call(engine_path(root, name), args, root, env)
        results.append(f"{name} {' '.join(args[:2])}")
    return {"ok": True, "checks": results}


def sift_action(root: Path, python: Path, action: str, params: Optional[Dict[str, Any]], env: Dict[str, str]) -> Dict[str, Any]:
    exe = engine_path(root, "RocogiSift")
    if exe.exists():
        return engine_call(exe, ["--action", action, "--params", json.dumps(params or {}, ensure_ascii=False)], root, env)
    code = (
        "import json,sys;from app.engine_sift import dispatch;"
        "print(json.dumps(dispatch(sys.argv[1], json.loads(sys.argv[2])), ensure_ascii=False))"
    )
    result = run(
        [str(python), "-c", code, action, json.dumps(params or {}, ensure_ascii=False)],
        cwd=root,
        env=env,
        capture=True,
    )
    data = json.loads(result.stdout.strip().splitlines()[-1])
    if data.get("ok") is False:
        raise DeployError(f"SIFT 动作失败: {data.get('error')}")
    return data


def ensure_sift(root: Path, python: Path, repo: str, tag: str, env: Dict[str, str], skip: bool) -> Dict[str, Any]:
    if skip:
        return {"skipped": True}
    log("准备可选 SIFT 包")
    target = root / "optional/sift-tracker"
    target.mkdir(parents=True, exist_ok=True)
    if not any(target.glob("*.zip")):
        require("gh")
        patterns = [
            "rocogi-sift-tracker-*.zip",
            "rocogi-sift-tracker-*-README.md",
            "rocogi-sift-tracker-*-manifest.json",
            "rocogi-sift-tracker-*-CHECKSUM.txt",
        ]
        for pattern in patterns:
            run(
                ["gh", "release", "download", tag, "-R", repo, "--pattern", pattern, "-D", str(target), "--clobber"],
                cwd=root,
                env=env,
            )
    info = sift_action(root, python, "tracker_info", {}, env)
    if not info.get("archiveExists"):
        raise DeployError(f"未找到 SIFT 压缩包: {target}")
    if not info.get("clientExists"):
        log("解包 SIFT 客户端（约 618 MB）")
        info = sift_action(root, python, "tracker_prepare", {}, env)
    if not info.get("clientExists"):
        raise DeployError("SIFT 包解包后未找到 SiftMapTracker.Client.exe")
    return {
        "archive": info.get("archive"),
        "client": info.get("client"),
        "clientExists": info.get("clientExists"),
        "launchable": info.get("launchable"),
    }


def http_json(port: int, path: str, timeout: float = 5.0) -> Any:
    url = f"http://127.0.0.1:{port}{path}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def try_health(port: int) -> Optional[Dict[str, Any]]:
    try:
        data = http_json(port, "/api/health", timeout=2.0)
        return data if data.get("service") == "rocoflow" else None
    except Exception:
        return None


def start_server(root: Path, python: Path, port: int, env: Dict[str, str]) -> Optional[subprocess.Popen]:
    health = try_health(port)
    if health:
        print(f"[deploy] 端口 {port} 已有 Rocogi 服务，直接复用")
        return None
    deploy_dir = root / "runtime/deploy"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    out = open(deploy_dir / "server.out.log", "a", encoding="utf-8")
    err = open(deploy_dir / "server.err.log", "a", encoding="utf-8")
    command = [
        str(python),
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        "backend",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    print("[run] " + " ".join(command), flush=True)
    process = subprocess.Popen(command, cwd=str(root), env=env, stdout=out, stderr=err, text=True)
    (deploy_dir / "server.pid").write_text(str(process.pid), encoding="utf-8")
    for _ in range(90):
        time.sleep(1)
        if process.poll() is not None:
            raise DeployError(f"服务启动失败，查看日志: {deploy_dir / 'server.err.log'}")
        if try_health(port):
            return process
    raise DeployError(f"服务 90 秒内未就绪，查看日志: {deploy_dir / 'server.err.log'}")


def verify_api(root: Path, port: int, env: Dict[str, str], engines: Dict[str, Any] | None, sift: Dict[str, Any]) -> Dict[str, Any]:
    log("验证 API")
    health = http_json(port, "/api/health")
    components = http_json(port, "/api/components")
    dex_meta = http_json(port, "/api/dex/meta")
    workflows = http_json(port, "/api/workflows")
    pokemon = http_json(port, "/api/battle/pokemon?limit=5")
    stats = components["stats"]
    checks = {
        "health": health.get("ok") is True,
        "noMemoryRead": health.get("platform", {}).get("reads_game_memory") is False,
        "componentCount": stats.get("componentCount") == 39,
        "gapCount": stats.get("gapCount") == 0,
        "dex": dex_meta.get("total", 0) >= 400,
        "workflows": len(workflows) >= 3,
        "battle": len(pokemon.get("items", [])) >= 1,
    }
    failed = [name for name, value in checks.items() if not value]
    report = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "root": str(root),
        "port": port,
        "checks": checks,
        "stats": stats,
        "health": health,
        "dex": {"total": dex_meta.get("total"), "skills": dex_meta.get("skillTotal")},
        "workflowCount": len(workflows),
        "engines": engines,
        "sift": sift,
    }
    deploy_dir = root / "runtime/deploy"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    (deploy_dir / "verify.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failed:
        raise DeployError(f"API 验证失败: {', '.join(failed)}，报告: {deploy_dir / 'verify.json'}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Rocogi 本地部署与验证")
    parser.add_argument("--root", default=DEFAULT_ROOT, help="部署目录")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-pull", action="store_true")
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--force-frontend", action="store_true")
    parser.add_argument("--skip-engines", action="store_true")
    parser.add_argument("--build-engines", action="store_true", help="非 Windows 环境也构建引擎")
    parser.add_argument("--skip-sift", action="store_true")
    parser.add_argument("--stop-after-verify", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    root = root.resolve()
    try:
        ensure_repo(root, args.repo, args.no_pull)
        env = build_env(root)
        python = ensure_dependencies(root, env, args.skip_deps)
        ensure_frontend(root, env, args.force_frontend, args.skip_frontend)
        run_tests(root, python, env, args.skip_tests)
        built = build_engines(root, env, args.build_engines, args.skip_engines)
        engines = verify_engines(root, env) if built else None
        sift = ensure_sift(root, python, args.repo, args.tag, env, args.skip_sift)
        process = start_server(root, python, args.port, env)
        report = verify_api(root, args.port, env, engines, sift)
        if process and args.stop_after_verify:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            print("[deploy] 验证完成，服务已停止")
        else:
            print(f"[deploy] 验证完成，服务运行在 http://127.0.0.1:{args.port}")
        print(json.dumps(report["checks"], ensure_ascii=False, indent=2))
        return 0
    except DeployError as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
