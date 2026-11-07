#!/usr/bin/env bash
# Build the headless Rocogi engine executables on Linux/macOS.
# Windows users should run scripts/build-engines.ps1 instead; PyInstaller does
# not cross-compile and a Windows .exe must be produced on Windows.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-$ROOT/.venv/bin/python}"
PIP="${PIP:-$ROOT/.venv/bin/pip}"
if [ ! -x "$PY" ]; then
  PY=python3
  PIP=pip3
fi

if ! "$PY" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "[install] pyinstaller"
  "$PIP" install -q pyinstaller
fi

DIST="$ROOT/dist/engines"
WORK="$ROOT/build/engines"
SPEC="$ROOT/build/specs"
mkdir -p "$DIST" "$WORK" "$SPEC"

EXCLUDES=(
  --exclude-module fastapi
  --exclude-module uvicorn
  --exclude-module websockets
  --exclude-module starlette
  --exclude-module pydantic
  --exclude-module app.api
  --exclude-module app.main
  --exclude-module app.harness
)

DATA=(--add-data "$ROOT/data:data")
VENDOR=(
  --paths "backend/vendor/nrc_ai"
  --hidden-import src.battle
  --hidden-import src.mcts
  --hidden-import src.team_builder
  --hidden-import src.models
  --hidden-import src.pokemon_db
  --hidden-import src.skill_db
  --hidden-import src.effect_engine
  --hidden-import src.effect_models
  --hidden-import src.effect_data
  --hidden-import src.skill_effects_generated
  --hidden-import src.pokemon_nature_table
  --add-data "$ROOT/backend/vendor/nrc_ai/data:backend/vendor/nrc_ai/data"
)

build() {
  local name="$1" entry="$2" hidden="$3" extra="$4"
  echo "[build] $name"
  # shellcheck disable=SC2086
  "$PY" -m PyInstaller \
    --noconfirm --clean --onefile \
    --name "$name" \
    --paths backend \
    --hidden-import "$hidden" \
    "${EXCLUDES[@]}" \
    ${extra} \
    --distpath "$DIST" \
    --workpath "$WORK/$name" \
    --specpath "$SPEC" \
    "packaging/entries/$entry.py" >/dev/null
  echo "[done] $DIST/$name"
}

build RocogiSense engine_sense app.engine_sense "${DATA[*]:-}"
build RocogiInput engine_input app.engine_input ""
build RocogiSift engine_sift app.engine_sift "${DATA[*]:-}"
build RocogiBattle engine_battle app.engine_battle "${DATA[*]:-} ${VENDOR[*]:-}"
build RocogiFlow engine_flow app.engine_flow "${DATA[*]:-} ${VENDOR[*]:-}"
build RocogiEngine engine_core app.engine_core "${DATA[*]:-} ${VENDOR[*]:-}"

echo ""
echo "Engine executables: $DIST"
( cd "$DIST" && sha256sum Rocogi* > checksums.txt )
ls -lh "$DIST"
