"""D2R Vault — Demo Mode sample data (spec §49)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.parser.item_parser import parse_item
from app.services.character_service import CharacterService
from app.services.item_service import ItemService
from app.services.inventory_service import InventoryService

SAMPLE_CHARACTERS = [
    {"name": "FrozenOrb", "char_class": "Sorceress", "level": 91, "difficulty": "Hell"},
    {"name": "Hammerdin", "char_class": "Paladin", "level": 93, "difficulty": "Hell"},
    {"name": "Whirlwind", "char_class": "Barbarian", "level": 88, "difficulty": "Hell"},
    {"name": "Javazon", "char_class": "Amazon", "level": 85, "difficulty": "Hell"},
]

SAMPLE_ITEM_TOOLTIPS = [
    "Harlequin Crest\nShako\nDefense: 98\n+2 To All Skills\n+1 To All Attributes\n"
    "+50% Enhanced Defense\nDamage Reduced By 10%\n+5% To Maximum Life\n+5% To Maximum Mana\nUnique",
    "Stone of Jordan\n+1 To All Skills\n+20 To Mana\nMaximum Mana +25%\nUnique",
    "Spirit\nRuneword\n+2 To All Skills\n+35% Faster Cast Rate\nFire Resist +30%\nCold Resist +30%",
    "The Oculus\nSwirling Crystal\n+3 To Sorceress Skill Levels\n+30% Faster Cast Rate\nUnique",
    "Ethereal Sword\nDamage: 15-25\nRequired Level: 20\nSocketed (2)\nEthereal (Cannot Be Repaired)",
]


def load_demo_data(session: Session) -> None:
    """Idempotent-ish: skips creating characters if any already exist,
    so re-launching in demo mode doesn't keep duplicating data."""
    char_service = CharacterService(session)
    if char_service.list_characters():
        return

    item_service = ItemService(session)
    inv_service = InventoryService(session)

    for char_def in SAMPLE_CHARACTERS:
        character = char_service.create_character(**char_def)
        for i, tooltip in enumerate(SAMPLE_ITEM_TOOLTIPS):
            parsed = parse_item(tooltip, ocr_confidence=97.5)
            container = "Personal Stash" if i % 2 == 0 else "Inventory"
            slot = inv_service.find_free_slot(character.id, container, 1, 1) or (0, 0)
            item_service.save_parsed_item(
                parsed, character.id, container=container, x=slot[0], y=slot[1], force=True,
            )
