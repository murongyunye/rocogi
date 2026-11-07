from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("backend/app", "sdk", "scripts", "packaging")
FORBIDDEN = re.compile(
    r"ReadProcessMemory|WriteProcessMemory|OpenProcess|process_vm_readv|"
    r"pymem|memory_reader|MemRead|/proc/\d+/mem",
    re.IGNORECASE,
)


def test_no_game_memory_reading_apis():
    """The engine may use screenshots and input only, never game process memory."""
    hits = []
    for folder in SCAN_DIRS:
        base = ROOT / folder
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in FORBIDDEN.finditer(text):
                hits.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
    assert not hits, "forbidden memory-reading API found: " + "; ".join(hits)
