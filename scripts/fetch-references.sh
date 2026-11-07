#!/usr/bin/env bash
# Clone the upstream projects used as references / data sources.
# The runtime only needs the data already committed under rocoflow/data and
# backend/vendor, so this script is optional.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$ROOT/references}"
mkdir -p "$TARGET"
cd "$TARGET"

# BetterGI is cloned for architecture / automation-flow reference only.
# Never import its Genshin datasets, task configs, maps or assets into Rocogi.
repos=(
  "https://github.com/yottaapp/yotta.git"
  "https://github.com/babalae/better-genshin-impact.git"
  "https://github.com/ColinHong10/NRC_AI.git"
  "https://github.com/Makapic/RocoPilot.git"
  "https://github.com/yorusacri/Auto-rocokingdom.git"
  "https://github.com/Wooziii/roco-map-tracker.git"
  "https://github.com/zh19990906/luoke_location.git"
  "https://github.com/SCH-CMYK/game-automation.git"
  "https://github.com/eachyczhang/-RocoTools.git rocotools"
  "https://github.com/rookie-orange/rocokingdom-ui.git"
  "https://github.com/Tsuann/RocoKingdom-AutoCapture.git"
  "https://github.com/Pacific-shark/roco-balance-lab.git"
  "https://github.com/ElliottZhao666666/rocom-codex-pets-gen.git"
  "https://github.com/Adolph321/-.git adolph-battle-rules"
)

for entry in "${repos[@]}"; do
  # shellcheck disable=SC2086
  set -- $entry
  repo="$1"
  name="${2:-$(basename "$repo" .git)}"
  if [ -d "$name/.git" ]; then
    echo "[skip] $name"
  else
    echo "[clone] $name"
    git clone --depth 1 "$repo" "$name"
  fi
done

echo ""
echo "Reference repositories are in: $TARGET"
echo "SIFT-Map-Tracker (Windows WPF client) is distributed via the Quark link"
echo "https://pan.quark.cn/s/bb51fb772eec and is not bundled here."
