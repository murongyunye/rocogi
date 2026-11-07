"""hud_selftest - prove the battle HUD parser without needing a live battle frame.

Fake OCR lines only; geometry comes from hud.REGIONS. Covers:
  * a battle frame (ally top-left, enemy top-right, 1..4 skill column, options bottom-right)
  * a field frame (only the own-pet panel + the single field skill)
  * OCR damage this game's HUD produces ("1D4/104" instead of "104/104", "10纟" for "10级")

Run:  python suite/probes/hud_selftest.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SUITE, "engines", "battle"))

import hud  # noqa: E402

W, H = 1280, 800
CATALOG = ["拍击", "甩水", "水枪", "音波弹", "升龙咆哮", "冷风"]

BATTLE = [
    {"text": "鸭吉吉", "cx": 125, "cy": 114},
    {"text": "10级", "cx": 303, "cy": 115},
    {"text": "104 / 104", "cx": 206, "cy": 150},
    {"text": "水", "cx": 150, "cy": 186},
    {"text": "3", "cx": 240, "cy": 186},
    {"text": "野生·小独角兽", "cx": 1120, "cy": 116},
    {"text": "12级", "cx": 1180, "cy": 116},
    {"text": "88 / 96", "cx": 1100, "cy": 152},
    {"text": "草", "cx": 1160, "cy": 186},
    {"text": "1", "cx": 40, "cy": 300},
    {"text": "拍击", "cx": 110, "cy": 302},
    {"text": "2", "cx": 40, "cy": 420},
    {"text": "甩水", "cx": 110, "cy": 422},
    {"text": "3", "cx": 40, "cy": 540},
    {"text": "水枪", "cx": 110, "cy": 542},
    {"text": "4", "cx": 40, "cy": 660},
    {"text": "音波弹", "cx": 110, "cy": 662},
    {"text": "逃跑", "cx": 1100, "cy": 700},
    {"text": "换精灵", "cx": 1180, "cy": 700},
]

FIELD = [
    {"text": "鸭吉吉", "cx": 125, "cy": 114},
    {"text": "10纟", "cx": 303, "cy": 115},
    {"text": "1D4/104", "cx": 206, "cy": 150},
    {"text": "音波弹", "cx": 417, "cy": 721},
]


def check(label, actual, expected):
    ok = actual == expected
    print(f"  [{'ok' if ok else 'FAIL'}] {label}: {actual!r}" + ("" if ok else f" != {expected!r}"))
    return ok


def main() -> int:
    ok = True
    print("battle frame:")
    read = hud.read(BATTLE, W, H, CATALOG)
    ok &= check("phase", read["phase"], "battle")
    ok &= check("battleScore", read["battleScore"], 3)
    ok &= check("ally name", read["ally"]["name"], "鸭吉吉")
    ok &= check("ally hp", (read["ally"]["hp"], read["ally"]["hpMax"]), (104, 104))
    ok &= check("ally level", read["ally"]["level"], 10)
    ok &= check("ally element", read["ally"]["element"], "水")
    ok &= check("enemy name", read["enemy"]["name"], "野生·小独角兽")
    ok &= check("enemy hp", (read["enemy"]["hp"], read["enemy"]["hpMax"]), (88, 96))
    ok &= check("enemy element", read["enemy"]["element"], "草")
    ok &= check("enemy hpPct", read["enemy"]["hpPct"], 91.7)
    slots = [(s["slot"], s["name"], s.get("source")) for s in read["skills"]]
    ok &= check("skill slots", slots,
                [(1, "拍击", "catalog"), (2, "甩水", "catalog"),
                 (3, "水枪", "catalog"), (4, "音波弹", "catalog")])
    ok &= check("keys", [s["key"] for s in read["skills"]], ["1", "2", "3", "4"])
    ok &= check("options", [o["text"] for o in read["options"]], ["逃跑", "换精灵"])

    print("field frame:")
    field = hud.read(FIELD, W, H, CATALOG)
    ok &= check("phase", field["phase"], "world")
    ok &= check("battleScore", field["battleScore"], 0)
    ok &= check("ally hp (OCR 1D4)", (field["ally"]["hp"], field["ally"]["hpMax"]), (104, 104))
    ok &= check("ally level (OCR 10纟)", field["ally"]["level"], 10)
    ok &= check("worldSkill", (field["worldSkill"] or {}).get("name"), "音波弹")

    print("parsers:")
    ok &= check("hp with spaces", hud.parse_hp("104 / 104"), (104, 104))
    ok &= check("hp rejects garbage", hud.parse_hp("00000會10"), None)
    ok &= check("level strict", hud.parse_level("Lv 12"), 12)
    ok &= check("level loose", hud.parse_level_loose("10纟"), 10)
    ok &= check("level loose rejects hp", hud.parse_level_loose("104/104"), None)
    print("PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
