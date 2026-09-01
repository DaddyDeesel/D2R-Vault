"""
D2R Vault — stat line parser.

Turns individual normalized tooltip lines (e.g. "+2 To All Skills",
"Fire Resist +30%", "35% Faster Cast Rate") into structured
(field_name, value) pairs. Designed to be tolerant of OCR noise: each
pattern matches loosely on the numeric part and a few keyword variants.

This module is pure string/regex logic with no external dependencies,
so it can be unit tested directly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParsedStatLine:
    field: str | None          # maps to an Item column, or None if unmapped
    value: int | float | None
    raw_line: str
    extra_key: str | None = None  # set when field is None, for extra_mods


# Each entry: (regex, target_field). Regexes are checked in order;
# first match wins. `%?` etc. tolerate OCR sometimes dropping symbols.
_NUM = r"([+-]?\d+)"

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"^{_NUM}\s*%?\s*to\s*all\s*skills$", re.I), "plus_to_skills"),
    (re.compile(rf"^{_NUM}\s*%?\s*faster\s*cast\s*rate$", re.I), "faster_cast_rate"),
    (re.compile(rf"^{_NUM}\s*%?\s*faster\s*hit\s*recovery$", re.I), "faster_hit_recovery"),
    (re.compile(rf"^{_NUM}\s*%?\s*faster\s*run/?walk$", re.I), "faster_run_walk"),
    (re.compile(rf"^{_NUM}\s*%?\s*life\s*stolen\s*per\s*hit$", re.I), "life_leech"),
    (re.compile(rf"^{_NUM}\s*%?\s*mana\s*stolen\s*per\s*hit$", re.I), "mana_leech"),
    (re.compile(rf"^{_NUM}\s*%?\s*(better\s*chance\s*of\s*getting\s*magic\s*items|magic\s*find)$", re.I), "magic_find"),
    (re.compile(rf"^{_NUM}\s*%?\s*extra\s*gold\s*from\s*monsters$", re.I), "gold_find"),
    (re.compile(rf"^{_NUM}\s*%?\s*chance\s*of\s*crushing\s*blow$", re.I), "crushing_blow"),
    (re.compile(rf"^{_NUM}\s*%?\s*deadly\s*strike$", re.I), "deadly_strike"),
    (re.compile(rf"^{_NUM}\s*%?\s*open\s*wounds?$", re.I), "open_wounds"),
    (re.compile(rf"^all\s*resistances?\s*{_NUM}\s*%?$", re.I), "all_resistances"),
    (re.compile(rf"^{_NUM}\s*%?\s*to\s*all\s*resistances?$", re.I), "all_resistances"),
    (re.compile(rf"^defense\s*[:]?\s*{_NUM}$", re.I), "defense"),
    (re.compile(rf"^{_NUM}\s*%?\s*enhanced\s*defense$", re.I), "enhanced_defense"),
    (re.compile(rf"^{_NUM}\s*%?\s*enhanced\s*damage$", re.I), "enhanced_damage"),
    (re.compile(rf"^\+\s*{_NUM}\s*to\s*(strength|str)$", re.I), "strength"),
    (re.compile(rf"^\+\s*{_NUM}\s*to\s*(dexterity|dex)$", re.I), "dexterity"),
    (re.compile(rf"^\+\s*{_NUM}\s*to\s*(vitality|vit)$", re.I), "vitality"),
    (re.compile(rf"^\+\s*{_NUM}\s*to\s*(energy|enr)$", re.I), "energy"),
    (re.compile(rf"^\+\s*{_NUM}\s*to\s*(life|hit\s*points)$", re.I), "life"),
    (re.compile(rf"^{_NUM}\s*%?\s*to\s*maximum\s*life$", re.I), "life"),
    (re.compile(rf"^\+\s*{_NUM}\s*to\s*mana$", re.I), "mana"),
    (re.compile(rf"^{_NUM}\s*%?\s*to\s*maximum\s*mana$", re.I), "mana"),
    (re.compile(rf"^required\s*level\s*[:]?\s*{_NUM}$", re.I), "required_level"),
    (re.compile(rf"^required\s*strength\s*[:]?\s*{_NUM}$", re.I), "required_strength"),
    (re.compile(rf"^required\s*dexterity\s*[:]?\s*{_NUM}$", re.I), "required_dexterity"),
    (re.compile(rf"^durability\s*[:]?\s*{_NUM}\s*(of\s*\d+)?$", re.I), "durability"),
]

_RESIST_PATTERN = re.compile(
    rf"^(fire|cold|lightning|poison)\s*resist(ance)?\s*{_NUM}\s*%?$", re.I
)

_DAMAGE_PATTERN = re.compile(r"^(one|two)?-?hand(ed)?\s*damage\s*[:]?\s*(\d+)\s*to\s*(\d+)$", re.I)
_DAMAGE_PATTERN_SIMPLE = re.compile(r"^damage\s*[:]?\s*(\d+)\s*[-to]+\s*(\d+)$", re.I)

_SOCKET_PATTERN = re.compile(r"^socketed\s*\((\d+)\)$", re.I)
_ETHEREAL_PATTERN = re.compile(r"^ethereal.*", re.I)

_SKILL_PATTERN = re.compile(
    rf"^\+\s*{_NUM}\s*to\s+(?P<skill>[A-Za-z' ]+?)(\s*\((?P<tab>[A-Za-z]+)\s*(only)?\))?$",
    re.I,
)


def parse_resistance_line(line: str) -> tuple[str, int] | None:
    m = _RESIST_PATTERN.match(line.strip())
    if not m:
        return None
    element = m.group(1).lower()
    value = int(m.group(3))
    return element, value


def parse_damage_line(line: str) -> tuple[int, int] | None:
    m = _DAMAGE_PATTERN.match(line.strip())
    if m:
        return int(m.group(3)), int(m.group(4))
    m = _DAMAGE_PATTERN_SIMPLE.match(line.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def parse_socket_line(line: str) -> int | None:
    m = _SOCKET_PATTERN.match(line.strip())
    return int(m.group(1)) if m else None


def is_ethereal_line(line: str) -> bool:
    return bool(_ETHEREAL_PATTERN.match(line.strip()))


def parse_skill_line(line: str) -> dict | None:
    """Parses lines like '+3 To Fire Ball (Sorceress Only)' into a skill
    dict. Deliberately excludes generic 'To All Skills' (handled by the
    dedicated pattern above) so skills aren't double-counted."""
    stripped = line.strip()
    if re.match(rf"^{_NUM}\s*%?\s*to\s*all\s*skills$", stripped, re.I):
        return None
    m = _SKILL_PATTERN.match(stripped)
    if not m:
        return None
    skill_name = m.group("skill").strip()
    if skill_name.lower() in {"all skills", "all attributes"}:
        return None
    return {
        "skill": skill_name.title(),
        "amount": int(m.group(1)),
        "tab": (m.group("tab") or "").title() or None,
    }


def parse_stat_line(line: str) -> ParsedStatLine:
    """Attempt to classify a single normalized tooltip line into a
    known Item field. Falls back to an unmapped extra-mod entry so no
    information is ever silently discarded."""
    stripped = line.strip()
    if not stripped:
        return ParsedStatLine(field=None, value=None, raw_line=line)

    for pattern, target_field in _PATTERNS:
        m = pattern.match(stripped)
        if m:
            value = int(m.group(1))
            return ParsedStatLine(field=target_field, value=value, raw_line=line)

    # Handled by dedicated multi-value parsers upstream (resist, damage,
    # sockets, skills) — if none of those match either, keep it raw.
    return ParsedStatLine(field=None, value=None, raw_line=line, extra_key=stripped)
