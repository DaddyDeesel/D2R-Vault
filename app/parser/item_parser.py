"""
D2R Vault — item parser.

Converts normalized OCR text of a D2R tooltip into a structured,
Pydantic-validated ParsedItem, using:
  - normalize.py for text cleanup + fuzzy name matching
  - stat_parser.py for line-by-line stat extraction
  - item_database.py for fuzzy matching against known items

Never raises on malformed input: if parsing can't confidently
determine a field, it's left None/empty and the raw OCR text is always
preserved (spec §41 — never discard captured information).
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.config import ITEM_QUALITIES
from app.parser import item_database, stat_parser
from app.parser.normalize import best_fuzzy_match, normalize_ocr_text

_QUALITY_KEYWORDS = {
    "unique": "Unique",
    "set item": "Set",
    "rare": "Rare",
    "crafted": "Crafted",
    "superior": "Superior",
    "magic": "Magic",
    "rune": "Rune",
    "gem": "Gem",
    "charm": "Charm",
    "jewel": "Jewel",
    "quest item": "Quest",
}


class ParsedSkill(BaseModel):
    skill: str
    amount: int
    tab: Optional[str] = None


class ParsedItem(BaseModel):
    """Structured result of parsing a tooltip. Mirrors the Item ORM
    model's field names 1:1 so services can map it directly."""

    name: str
    base_name: Optional[str] = None
    quality: str = "Normal"
    item_type: Optional[str] = None
    ethereal: bool = False
    socket_count: int = 0

    required_level: Optional[int] = None
    required_strength: Optional[int] = None
    required_dexterity: Optional[int] = None

    defense: Optional[int] = None
    damage_min: Optional[int] = None
    damage_max: Optional[int] = None
    durability: Optional[int] = None
    enhanced_damage: Optional[int] = None
    enhanced_defense: Optional[int] = None

    strength: Optional[int] = None
    dexterity: Optional[int] = None
    vitality: Optional[int] = None
    energy: Optional[int] = None
    life: Optional[int] = None
    mana: Optional[int] = None

    resistances: dict = Field(default_factory=dict)
    all_resistances: Optional[int] = None

    skills: list[ParsedSkill] = Field(default_factory=list)
    plus_to_skills: Optional[int] = None

    faster_cast_rate: Optional[int] = None
    faster_hit_recovery: Optional[int] = None
    faster_run_walk: Optional[int] = None
    life_leech: Optional[int] = None
    mana_leech: Optional[int] = None
    magic_find: Optional[int] = None
    gold_find: Optional[int] = None
    crushing_blow: Optional[int] = None
    deadly_strike: Optional[int] = None
    open_wounds: Optional[int] = None

    extra_mods: dict = Field(default_factory=dict)
    reference_item_name: Optional[str] = None
    reference_match_score: float = 0.0

    raw_ocr_text: str = ""
    ocr_confidence: Optional[float] = None
    low_confidence_fields: list[str] = Field(default_factory=list)


def detect_quality(lines: list[str]) -> str:
    joined = " ".join(lines).lower()
    for keyword, quality in _QUALITY_KEYWORDS.items():
        if keyword in joined:
            return quality
    return "Normal"


def detect_name_and_base(lines: list[str], quality: str) -> tuple[str, Optional[str]]:
    """The item name is virtually always the first non-empty line(s) of
    a D2R tooltip, sometimes followed by a base-type line for uniques
    (e.g. 'Harlequin Crest' / 'Shako'). Fuzzy-match both against the
    reference DB to correct OCR noise."""
    content_lines = [l for l in lines if l.strip()]
    if not content_lines:
        return "Unknown Item", None

    raw_name = content_lines[0].strip()
    candidates = item_database.all_item_names()
    matched_name, score = best_fuzzy_match(raw_name, candidates)
    final_name = matched_name if matched_name else raw_name

    base_name = None
    if quality in ("Unique", "Set") and len(content_lines) > 1:
        raw_base = content_lines[1].strip()
        base_candidates = item_database.item_names_by_category("base")
        matched_base, base_score = best_fuzzy_match(raw_base, base_candidates)
        base_name = matched_base if matched_base else (raw_base if len(raw_base) < 40 else None)

    return final_name, base_name


def parse_item(raw_ocr_text: str, ocr_confidence: float | None = None) -> ParsedItem:
    """Main entry point. Never raises — worst case returns a ParsedItem
    with quality='Miscellaneous' and only raw_ocr_text populated, so the
    caller can always fall back to manual entry (spec §41)."""
    try:
        return _parse_item_inner(raw_ocr_text, ocr_confidence)
    except Exception:
        return ParsedItem(
            name=raw_ocr_text.strip().splitlines()[0][:120] if raw_ocr_text.strip() else "Unknown Item",
            quality="Miscellaneous",
            raw_ocr_text=raw_ocr_text,
            ocr_confidence=ocr_confidence,
        )


def _parse_item_inner(raw_ocr_text: str, ocr_confidence: float | None) -> ParsedItem:
    normalized = normalize_ocr_text(raw_ocr_text)
    lines = normalized.split("\n")

    quality = detect_quality(lines)
    name, base_name = detect_name_and_base(lines, quality)

    result = ParsedItem(
        name=name,
        base_name=base_name,
        quality=quality if quality in ITEM_QUALITIES else "Normal",
        raw_ocr_text=raw_ocr_text,
        ocr_confidence=ocr_confidence,
    )

    resistances: dict = {}
    low_confidence: list[str] = []

    # Skip the first 1-2 identity lines already consumed above.
    stat_lines = lines[2:] if base_name else lines[1:]

    for line in stat_lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stat_parser.is_ethereal_line(stripped):
            result.ethereal = True
            continue

        sockets = stat_parser.parse_socket_line(stripped)
        if sockets is not None:
            result.socket_count = sockets
            continue

        resist = stat_parser.parse_resistance_line(stripped)
        if resist is not None:
            element, value = resist
            resistances[element] = value
            continue

        damage = stat_parser.parse_damage_line(stripped)
        if damage is not None:
            result.damage_min, result.damage_max = damage
            continue

        skill = stat_parser.parse_skill_line(stripped)
        if skill is not None:
            result.skills.append(ParsedSkill(**skill))
            continue

        parsed_line = stat_parser.parse_stat_line(stripped)
        if parsed_line.field is not None:
            setattr(result, parsed_line.field, parsed_line.value)
        elif parsed_line.extra_key:
            # Preserve anything we couldn't classify rather than drop it.
            result.extra_mods[parsed_line.extra_key] = True
            if len(parsed_line.extra_key) > 2:
                low_confidence.append(parsed_line.extra_key)

    result.resistances = resistances
    result.low_confidence_fields = low_confidence

    ref_entry = item_database.find_entry(name)
    if ref_entry:
        result.reference_item_name = ref_entry["name"]
        result.reference_match_score = 1.0
        if not result.item_type:
            result.item_type = ref_entry.get("category")

    return result



_UI_LABELS = {
    "gems", "runes", "keys", "misc", "personal", "shared", "shared stash",
    "personal stash", "stash", "inventory", "cube", "horadric cube",
    "mercenary", "character", "skill tree", "skills", "quests", "waypoint",
    "repair", "trade", "buy", "sell", "gold", "deposit", "withdraw",
    "close", "cancel", "accept", "gamble", "socket", "transmute",
}

_ITEM_SIGNAL_PATTERNS = [
    re.compile(r"\bdefense\s*[:]?\s*\d+", re.I),
    re.compile(r"\b(?:one|two)?-?hand(?:ed)?\s+damage\b|\bdamage\s*[:]?\s*\d+", re.I),
    re.compile(r"\brequired\s+(?:level|strength|dexterity)\b", re.I),
    re.compile(r"\bdurability\b", re.I),
    re.compile(r"\bsocketed\s*\(\d+\)", re.I),
    re.compile(r"\bethereal\b", re.I),
    re.compile(r"[+-]\s*\d+\s*%?\s+(?:to|faster|enhanced|chance|all|life|mana|fire|cold|lightning|poison)", re.I),
    re.compile(r"\b(?:fire|cold|lightning|poison)\s+resist", re.I),
    re.compile(r"\b(?:weapon|armor|shield)\s*[:]?", re.I),
    re.compile(r"\bcan be inserted into socketed items\b", re.I),
]


def validate_item_capture(parsed: ParsedItem, raw_ocr_text: str) -> tuple[bool, str, int]:
    """Reject obvious D2R UI chrome while staying permissive for real items.

    Returns (is_valid, reason, evidence_score). This deliberately does not
    require a known reference-db match because the bundled DB is only a seed.
    """
    normalized = normalize_ocr_text(raw_ocr_text)
    lines = [ln.strip() for ln in normalized.splitlines() if ln.strip()]
    if not lines:
        return False, "No tooltip text was detected", 0

    first = re.sub(r"[^a-z0-9' ]+", "", lines[0].lower()).strip()
    if first in _UI_LABELS and len(lines) <= 2:
        return False, f"'{lines[0]}' looks like a stash/UI label, not an item tooltip", 0

    # A single unknown word/short phrase is almost always UI chrome. Known
    # item names are allowed so simple rune/base captures still work.
    ref = item_database.find_entry(parsed.name)
    if len(lines) == 1 and ref is None:
        return False, "Only a UI-style label was detected; hover the item until its tooltip is visible", 0

    score = 0
    if ref is not None:
        score += 3
    if parsed.defense is not None or parsed.damage_min is not None:
        score += 3
    if parsed.required_level is not None or parsed.required_strength is not None or parsed.required_dexterity is not None:
        score += 2
    if parsed.socket_count or parsed.ethereal or parsed.durability is not None:
        score += 2
    if parsed.skills or parsed.plus_to_skills is not None or parsed.resistances or parsed.all_resistances is not None:
        score += 2
    if any(v is not None for v in (parsed.enhanced_damage, parsed.enhanced_defense, parsed.faster_cast_rate,
                                    parsed.faster_hit_recovery, parsed.faster_run_walk, parsed.magic_find,
                                    parsed.gold_find, parsed.life_leech, parsed.mana_leech)):
        score += 2
    joined = "\n".join(lines)
    score += min(3, sum(1 for pat in _ITEM_SIGNAL_PATTERNS if pat.search(joined)))
    if len(lines) >= 3:
        score += 1
    if len(lines) >= 5:
        score += 1

    # Multi-line tooltips are allowed even when OCR misses structured stats, but
    # two-line/no-signal captures are too likely to be menus/tabs.
    if score < 2 and len(lines) <= 2:
        return False, "The capture does not contain enough item-tooltip evidence", score
    return True, "", score


def compute_fingerprint(parsed: ParsedItem) -> str:
    """A stable hash used for duplicate detection (spec §15). Built from
    the fields most likely to distinguish genuinely different items,
    ignoring cosmetic/OCR-noise fields."""
    key_parts = [
        parsed.name.strip().lower(),
        parsed.quality,
        str(parsed.defense or ""),
        f"{parsed.damage_min or ''}-{parsed.damage_max or ''}",
        str(parsed.socket_count),
        str(parsed.ethereal),
        str(sorted(parsed.resistances.items())),
        str(sorted((s.skill, s.amount) for s in parsed.skills)),
        str(parsed.magic_find or ""),
        str(parsed.faster_cast_rate or ""),
    ]
    digest_input = "|".join(key_parts).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()[:32]
