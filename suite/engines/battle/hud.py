"""Battle HUD parsing - the layout the player described, in code.

    top-left    own pet:  HP (x / y), energy, party count, element, gender, level
    top-right   enemy pet: HP (x / y), energy, party count, element, gender, level
    left edge   four skill icons, numbered 1..4 - press the number to cast
    bottom-right options (flee / switch pet / ...)

Nothing here does OCR: feed it recognised lines (``{"text", "cx", "cy"}`` in frame
pixels) from whatever OCR backend is available, and it returns a structured read.
Keeping the parser OCR-free is deliberate - the battle engine venv has no OCR
dependency, and the same rules must work for WinRT OCR, tesseract or a future
vision model.
"""
from __future__ import annotations

import re
from typing import Iterable

# Fractional boxes (left, top, right, bottom) of the 1280x800 HUD.
REGIONS = {
    "ally": (0.00, 0.02, 0.40, 0.30),
    "enemy": (0.60, 0.02, 1.00, 0.30),
    "skills": (0.00, 0.24, 0.26, 0.92),
    "options": (0.55, 0.62, 1.00, 1.00),
    "world_skill": (0.24, 0.78, 0.52, 1.00),
}

HP_RE = re.compile(r"(\d{1,4})\s*[／/|]\s*(\d{1,4})")
LEVEL_RE = re.compile(r"(\d{1,3})\s*(?:级|級)|(?:级|級|Lv\.?|LV\.?|lv\.?)\s*(\d{1,3})")
SLOT_RE = re.compile(r"^\s*([1-4])\s*[.．、:]?\s*$")
DIGITS_RE = re.compile(r"\d{1,4}")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ELEMENTS = ("草", "火", "水", "土", "风", "冰", "雷", "光", "暗", "普通", "龙", "机械", "毒", "虫", "灵")


def zone_lines(lines: Iterable[dict], box, width: int, height: int) -> list[dict]:
    x1, y1, x2, y2 = box
    left, top, right, bottom = x1 * width, y1 * height, x2 * width, y2 * height
    out = []
    for line in lines:
        cx, cy = float(line.get("cx", 0)), float(line.get("cy", 0))
        if left <= cx <= right and top <= cy <= bottom:
            out.append(line)
    return sorted(out, key=lambda d: (float(d.get("cy", 0)), float(d.get("cx", 0))))


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def parse_hp(text: str) -> tuple[int, int] | None:
    m = HP_RE.search(_squash(text).replace("D", "0"))
    if not m:
        return None
    cur, top = int(m.group(1)), int(m.group(2))
    if top <= 0 or cur > top * 3:
        return None
    return cur, top


def parse_level(text: str) -> int | None:
    flat = _squash(text)
    m = LEVEL_RE.search(flat)
    if not m:
        return None
    value = m.group(1) or m.group(2)
    return int(value) if value else None


def parse_level_loose(text: str) -> int | None:
    """OCR often mangles 级 into a stray glyph ("10纟"), so accept a short
    "digits + at most two junk glyphs" line as a level when the strict form fails."""
    flat = _squash(text)
    m = re.fullmatch(r"(\d{1,3})[^\d/]{0,2}", flat)
    if not m:
        return None
    value = int(m.group(1))
    return value if 1 <= value <= 100 else None


def parse_small_int(text: str, lo: int = 0, hi: int = 999) -> int | None:
    for m in DIGITS_RE.finditer(_squash(text)):
        val = int(m.group(0))
        if lo <= val <= hi:
            return val
    return None


def find_element(text: str) -> str | None:
    flat = _squash(text)
    for el in ELEMENTS:
        if el in flat:
            return el
    return None


def pet_name_candidates(lines: list[dict]) -> list[str]:
    """CJK-only lines that are not labels, biggest first (a name is drawn large)."""
    out = []
    for line in lines:
        text = _squash(line.get("text"))
        if not text or not CJK_RE.search(text):
            continue
        if any(k in text for k in ("等级", "级", "能量", "生命", "血量", "属性", "性别", "回合")):
            continue
        out.append(text)
    return out


def read_side(lines: list[dict], width: int, height: int, box) -> dict:
    """Own or enemy pet panel: name, hp, energy, level, element, party count."""
    zone = zone_lines(lines, box, width, height)
    hp = None
    level = None
    element = None
    name = None
    leftovers: list[str] = []
    for line in zone:
        text = _squash(line.get("text"))
        if not text:
            continue
        if hp is None:
            hp = parse_hp(text)
        if level is None:
            level = parse_level(text)
        if element is None:
            element = find_element(text)
        if name is None and CJK_RE.search(text) and not DIGITS_RE.search(text):
            name = text
        if not any((hp, level, element)) or DIGITS_RE.search(text):
            leftovers.append(text)
    # energy / party count: small integers drawn as their own label
    ints = [parse_small_int(t, 0, 99) for t in leftovers]
    ints = [i for i in ints if i is not None]
    if level is None:
        # the level sits on the same baseline as the name, right of it
        name_cy = next((float(z["cy"]) for z in zone if _squash(z.get("text")) == name), None)
        for line in zone:
            text = _squash(line.get("text"))
            loose = parse_level_loose(text)
            if loose is None:
                continue
            if name_cy is None or abs(float(line.get("cy", 0)) - name_cy) <= 16:
                level = loose
                break
    return {
        "name": name,
        "hp": hp[0] if hp else None,
        "hpMax": hp[1] if hp else None,
        "hpPct": round(100.0 * hp[0] / hp[1], 1) if hp else None,
        "level": level,
        "element": element,
        "ints": ints[:6],
        "lines": [{"text": _squash(z.get("text")), "cx": z.get("cx"), "cy": z.get("cy")} for z in zone],
    }


def read_skills(lines: list[dict], width: int, height: int, known: Iterable[str] = ()) -> list[dict]:
    """The numbered skill column on the left edge.

    A slot is drawn as a bare digit "1".."4" plus the skill name on the same row, and
    OCR returns them as two separate lines, so digits are paired with the nearest name
    on their baseline. The number is what has to be pressed to cast.
    """
    known_norm = {_squash(k): k for k in known if k}
    zone = zone_lines(lines, REGIONS["skills"], width, height)

    digits: list[dict] = []
    names: list[dict] = []
    for line in zone:
        text = _squash(line.get("text"))
        if not text:
            continue
        if SLOT_RE.match(text):
            digits.append({"num": int(SLOT_RE.match(text).group(1)),
                           "cy": float(line.get("cy") or 0), "cx": float(line.get("cx") or 0)})
            continue
        if text in known_norm:
            names.append({"name": known_norm[text], "text": text, "source": "catalog",
                          "cy": float(line.get("cy") or 0), "cx": float(line.get("cx") or 0)})
        elif CJK_RE.search(text) and 1 < len(text) <= 6:
            names.append({"name": text, "text": text, "source": "guess",
                          "cy": float(line.get("cy") or 0), "cx": float(line.get("cx") or 0)})

    # one entry per name (OCR often repeats a label at several scales)
    deduped: list[dict] = []
    for name in sorted(names, key=lambda n: n["cy"]):
        if any(abs(name["cy"] - seen["cy"]) <= 8 and name["text"] == seen["text"] for seen in deduped):
            continue
        deduped.append(name)

    ROW_TOLERANCE = 26.0
    slots: list[dict] = []
    used: set[int] = set()
    for name in deduped:
        best = None
        for digit in digits:
            if digit["num"] in used:
                continue
            gap = abs(digit["cy"] - name["cy"])
            if gap > ROW_TOLERANCE:
                continue
            if best is None or gap < best[0]:
                best = (gap, digit)
        if best is not None:
            used.add(best[1]["num"])
            slots.append({"slot": best[1]["num"], "name": name["name"], "text": name["text"],
                          "cx": name["cx"], "cy": name["cy"], "source": name["source"]})
        else:
            slots.append({"slot": None, "name": name["name"], "text": name["text"],
                          "cx": name["cx"], "cy": name["cy"], "source": name["source"]})
    # unnumbered names fall back to their top-to-bottom order
    slots.sort(key=lambda s: s["cy"])
    next_free = 1
    for slot in slots:
        if slot["slot"] is None:
            while next_free in used:
                next_free += 1
            slot["slot"] = next_free
            used.add(next_free)
        slot["key"] = str(slot["slot"])
    slots.sort(key=lambda s: s["slot"])
    return slots


def read_options(lines: list[dict], width: int, height: int) -> list[dict]:
    zone = zone_lines(lines, REGIONS["options"], width, height)
    return [{"text": _squash(z.get("text")), "cx": z.get("cx"), "cy": z.get("cy")} for z in zone]


def read_world_skill(lines: list[dict], width: int, height: int) -> dict | None:
    """Field HUD: the single equipped skill drawn bottom-centre while exploring."""
    zone = zone_lines(lines, REGIONS["world_skill"], width, height)
    for line in zone:
        text = _squash(line.get("text"))
        if CJK_RE.search(text) and 1 < len(text) <= 6:
            return {"name": text, "cx": line.get("cx"), "cy": line.get("cy")}
    return None


def read(lines, width: int, height: int, known_skills: Iterable[str] = ()) -> dict:
    """Full HUD read: phase + both pet panels + skill slots + options."""
    lines = list(lines)
    ally = read_side(lines, width, height, REGIONS["ally"])
    enemy = read_side(lines, width, height, REGIONS["enemy"])
    skills = read_skills(lines, width, height, known_skills)
    options = read_options(lines, width, height)

    enemy_present = bool(enemy["lines"]) and (enemy["hp"] is not None or enemy["level"] is not None)
    skill_present = len([s for s in skills if s.get("name")]) >= 2
    option_present = len(options) >= 1
    score = sum((enemy_present, skill_present, option_present))
    phase = "battle" if score >= 2 else ("world" if ally["hp"] or ally["name"] else "unknown")

    return {
        "phase": phase,
        "battleScore": score,
        "evidence": {"enemyPanel": enemy_present, "skillColumn": skill_present,
                     "options": option_present},
        "ally": ally,
        "enemy": enemy,
        "skills": skills,
        "options": options,
        "worldSkill": read_world_skill(lines, width, height),
        "frame": {"width": width, "height": height},
    }
