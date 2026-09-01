"""
D2R Vault — local static item reference data.

A small seed set covering common bases/uniques/runewords, enough to
demonstrate fuzzy matching (spec §12) and populate Demo Mode (spec
§49). This is intentionally NOT a full, exhaustive dump of every D2R
item — it's a starting seed that `services/backup_service`-adjacent
tooling or a future data importer can extend. All values here are
well-known public game mechanics (base stats, item names), not
extracted from any copyrighted game asset file.
"""
from __future__ import annotations

# category in {"base", "unique", "set", "rune", "runeword", "gem", "jewel", "charm"}
SEED_ITEM_DATABASE: list[dict] = [
    # --- Bases ---
    {"name": "Shako", "category": "base", "base_type": "Cap", "required_level": 62,
     "fixed_stats": [], "variable_stats": []},
    {"name": "Monarch", "category": "base", "base_type": "Shield", "required_level": 45,
     "fixed_stats": [], "variable_stats": []},
    {"name": "Sword", "category": "base", "base_type": "Weapon", "required_level": 1,
     "fixed_stats": [], "variable_stats": []},

    # --- Uniques ---
    {"name": "Harlequin Crest", "category": "unique", "base_type": "Shako", "required_level": 62,
     "fixed_stats": [
         "+2 To All Skills", "+1 To All Attributes", "+50% Enhanced Defense",
         "Damage Reduced By 10%", "+5% To Maximum Life", "+5% To Maximum Mana",
     ],
     "variable_stats": [{"stat": "all_attributes", "min": 1, "max": 2}]},
    {"name": "Death's Fathom", "category": "unique", "base_type": "Round Shield", "required_level": 62,
     "fixed_stats": ["+2 To Sorceress Skill Levels", "+45% Faster Cast Rate"],
     "variable_stats": []},
    {"name": "Spirit", "category": "runeword", "base_type": "Sword/Shield", "required_level": 25,
     "fixed_stats": ["+2 To All Skills", "+25-35% Faster Cast Rate", "+55% Enhanced Damage"],
     "variable_stats": [{"stat": "faster_cast_rate", "min": 25, "max": 35}]},
    {"name": "Griffon's Eye", "category": "unique", "base_type": "Circlet", "required_level": 76,
     "fixed_stats": ["+1 To All Skills", "+20-30% Faster Cast Rate",
                      "-20% To Enemy Lightning Resistance"],
     "variable_stats": [{"stat": "faster_cast_rate", "min": 20, "max": 30}]},
    {"name": "Nightwing's Veil", "category": "unique", "base_type": "Spired Helm", "required_level": 66,
     "fixed_stats": ["+2 To Necromancer Skill Levels", "+2 To Curses"],
     "variable_stats": []},
    {"name": "Arachnid Mesh", "category": "unique", "base_type": "Spiderweb Sash", "required_level": 65,
     "fixed_stats": ["+1 To All Skills", "+20% Faster Cast Rate"],
     "variable_stats": []},
    {"name": "The Oculus", "category": "unique", "base_type": "Swirling Crystal", "required_level": 62,
     "fixed_stats": ["+3 To Sorceress Skill Levels", "+30% Faster Cast Rate"],
     "variable_stats": []},
    {"name": "Mara's Kaleidoscope", "category": "unique", "base_type": "Amulet", "required_level": 67,
     "fixed_stats": ["+2 To All Skills", "+20-30 To All Resistances"],
     "variable_stats": [{"stat": "all_resistances", "min": 20, "max": 30}]},
    {"name": "Stone of Jordan", "category": "unique", "base_type": "Ring", "required_level": 29,
     "fixed_stats": ["+1 To All Skills", "+20 To Mana", "Maximum Mana +25%"],
     "variable_stats": []},
    {"name": "Windforce", "category": "unique", "base_type": "Hydra Bow", "required_level": 73,
     "fixed_stats": ["Knockback", "+250-300% Enhanced Damage"],
     "variable_stats": [{"stat": "enhanced_damage", "min": 250, "max": 300}]},

    # --- Runes ---
    {"name": "El", "category": "rune", "required_level": 11, "fixed_stats": [], "variable_stats": []},
    {"name": "Ber", "category": "rune", "required_level": 63, "fixed_stats": [], "variable_stats": []},
    {"name": "Zod", "category": "rune", "required_level": 69, "fixed_stats": [], "variable_stats": []},
]


def item_names_by_category(category: str | None = None) -> list[str]:
    if category is None:
        return [entry["name"] for entry in SEED_ITEM_DATABASE]
    return [entry["name"] for entry in SEED_ITEM_DATABASE if entry["category"] == category]


def all_item_names() -> list[str]:
    return [entry["name"] for entry in SEED_ITEM_DATABASE]


def find_entry(name: str) -> dict | None:
    for entry in SEED_ITEM_DATABASE:
        if entry["name"] == name:
            return entry
    return None
