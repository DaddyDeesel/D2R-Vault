"""
D2R Vault — search service.

Provides structured filtering (spec §16/§17) plus a small deterministic
natural-language front-end (spec §32, "What do I have?") that maps
common question patterns to structured filters. No external AI API is
required for this to work.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.database.models import Character, Item
from app.database.repositories import ItemRepository


@dataclass
class ItemFilter:
    name_contains: str | None = None
    character_id: int | None = None
    character_class: str | None = None
    quality: str | None = None
    ethereal: bool | None = None
    min_sockets: int | None = None
    min_fcr: int | None = None
    min_fhr: int | None = None
    min_magic_find: int | None = None
    min_all_resist: int | None = None
    min_plus_skills: int | None = None
    stat_contains: str | None = None  # matches extra_mods keys / skill names


class SearchService:
    def __init__(self, session: Session):
        self.session = session
        self.items = ItemRepository(session)

    def search(self, f: ItemFilter) -> list[Item]:
        results = list(self.items.all())

        if f.character_id is not None:
            results = [i for i in results if i.character_id == f.character_id]
        if f.character_class is not None:
            results = [
                i for i in results
                if i.character and i.character.char_class.lower() == f.character_class.lower()
            ]
        if f.name_contains:
            needle = f.name_contains.lower()
            results = [i for i in results if needle in i.name.lower() or needle in (i.base_name or "").lower()]
        if f.quality is not None:
            results = [i for i in results if i.quality.lower() == f.quality.lower()]
        if f.ethereal is not None:
            results = [i for i in results if i.ethereal == f.ethereal]
        if f.min_sockets is not None:
            results = [i for i in results if i.socket_count >= f.min_sockets]
        if f.min_fcr is not None:
            results = [i for i in results if (i.faster_cast_rate or 0) >= f.min_fcr]
        if f.min_fhr is not None:
            results = [i for i in results if (i.faster_hit_recovery or 0) >= f.min_fhr]
        if f.min_magic_find is not None:
            results = [i for i in results if (i.magic_find or 0) >= f.min_magic_find]
        if f.min_all_resist is not None:
            results = [i for i in results if (i.all_resistances or 0) >= f.min_all_resist]
        if f.min_plus_skills is not None:
            results = [i for i in results if (i.plus_to_skills or 0) >= f.min_plus_skills]
        if f.stat_contains:
            needle = f.stat_contains.lower()
            results = [
                i for i in results
                if any(needle in (s.get("skill", "").lower()) for s in (i.skills or []))
                or any(needle in k.lower() for k in (i.extra_mods or {}).keys())
            ]
        return results


# ---------------------------------------------------------------------------
# Deterministic natural-language front-end
# ---------------------------------------------------------------------------

_FCR_RE = re.compile(r"(\d+)\s*%?\s*fcr|(\d+)\s*%?\s*faster\s*cast", re.I)
_SOCKET_RE = re.compile(r"(\d+)\s*(-|\s)?\s*socket", re.I)
_MF_RE = re.compile(r"(\d+)\s*%?\s*mf|(\d+)\s*%?\s*magic\s*find", re.I)


def parse_natural_query(question: str) -> ItemFilter:
    """Best-effort deterministic translation of a plain-English question
    into an ItemFilter. Unrecognized clauses are simply ignored rather
    than raising, so the search always runs (possibly broader than
    intended) instead of failing outright."""
    q = question.strip()
    f = ItemFilter()

    m = _FCR_RE.search(q)
    if m:
        f.min_fcr = int(m.group(1) or m.group(2))

    m = _SOCKET_RE.search(q)
    if m:
        f.min_sockets = int(m.group(1))

    m = _MF_RE.search(q)
    if m:
        f.min_magic_find = int(m.group(1) or m.group(2))

    if "ethereal" in q.lower():
        f.ethereal = True

    for quality in ("unique", "set", "rare", "magic", "runeword", "crafted", "charm"):
        if re.search(rf"\b{quality}\b", q, re.I):
            f.quality = quality.title()
            break

    # Known item names mentioned directly, e.g. "Do I have a Monarch?"
    known_words = re.findall(r"[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)*", question)
    if known_words:
        # Prefer the longest capitalized phrase as the likely item/base name.
        f.name_contains = max(known_words, key=len)

    return f
