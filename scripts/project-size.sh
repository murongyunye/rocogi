#!/usr/bin/env bash
# Report Rocogi project size by category.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

size() {
  local path="$1"
  if [ -e "$path" ]; then
    du -sh "$path" 2>/dev/null | awk '{print $1}'
  else
    echo "-"
  fi
}

echo "Rocogi project size"
echo "-------------------"
printf "total workspace      %s\n" "$(size .)"
printf "core source          %s (backend, data, frontend source/dist, docs md, scripts, sdk)\n" \
  "$(du -sh --exclude=.venv --exclude=frontend/node_modules --exclude=references --exclude=optional \
      --exclude=dist --exclude=build --exclude=runtime --exclude=release --exclude=docs/screenshots . 2>/dev/null | awk '{print $1}')"
printf "docs screenshots     %s\n" "$(size docs/screenshots)"
printf "runtime (generated)  %s\n" "$(size runtime)"
printf "build (generated)    %s\n" "$(size build)"
printf "dist engines         %s\n" "$(size dist/engines)"
printf "dev venv             %s\n" "$(size .venv)"
printf "dev node_modules     %s\n" "$(size frontend/node_modules)"
printf "references           %s\n" "$(size references)"
printf "optional SIFT bundle %s\n" "$(size optional/sift-tracker)"
printf "release archives     %s\n" "$(size release)"
