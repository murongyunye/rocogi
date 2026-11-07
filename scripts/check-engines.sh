#!/usr/bin/env bash
# Smoke test the built headless engines.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="${1:-$ROOT/dist/engines}"

run() {
  local name="$1"; shift
  echo "[check] $name"
  "$DIST/$name" "$@" | "$ROOT/.venv/bin/python" -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok'), d; print('  ok:', d.get('action') or d.get('engine'))"
}

run RocogiSense --action templates
run RocogiSense --action sprites
run RocogiSense --action ocr --params '{"roi":[0.03,0.86,0.25,0.06]}'
run RocogiSense --action foreground
run RocogiInput --action press --params '{"key":"x"}'
run RocogiInput --action hotkey
run RocogiSift --action route --params '{"labels":["宝箱"],"limit":2}'
run RocogiSift --action tracker_info
run RocogiBattle --action dex_detail --params '{"name":"迪莫"}'
run RocogiBattle --action analyze --params '{"team":["迪莫","喵喵"]}'
run RocogiBattle --action turn_state
run RocogiFlow --action workflows
run RocogiEngine --action library
run RocogiEngine --action sense.templates
run RocogiEngine --action sense.sprites
run RocogiEngine --action battle.turn_state
run RocogiEngine --action battle.analyze --params '{"team":["迪莫","喵喵"]}'
echo "all engine binaries passed"
