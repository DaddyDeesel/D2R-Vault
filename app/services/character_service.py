"""D2R Vault — character service: CRUD + dashboard statistics."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Character
from app.database.repositories import CharacterRepository, ItemRepository


class CharacterService:
    def __init__(self, session: Session):
        self.session = session
        self.characters = CharacterRepository(session)
        self.items = ItemRepository(session)

    def create_character(
        self, name: str, char_class: str, level: int = 1, difficulty: str = "Normal",
        season: str | None = None, hardcore: bool = False, ladder: bool = True,
    ) -> Character:
        if not name or not name.strip():
            raise ValueError("Character name is required.")
        return self.characters.create(
            name=name.strip(), char_class=char_class, level=level, difficulty=difficulty,
            season=season, hardcore=hardcore, ladder=ladder,
        )

    def update_character(self, character_id: int, **fields) -> Character | None:
        return self.characters.update(character_id, **fields)

    def delete_character(self, character_id: int) -> bool:
        return self.characters.delete(character_id)

    def list_characters(self) -> list[Character]:
        return list(self.characters.list_all())

    def dashboard_stats(self, character_id: int) -> dict:
        items = self.items.for_character(character_id)
        stats = {
            "total_items": len(items),
            "equipped_items": sum(1 for i in items if i.container == "Equipped"),
            "inventory_items": sum(1 for i in items if i.container == "Inventory"),
            "stash_items": sum(1 for i in items if i.container in ("Personal Stash", "Shared Stash")),
            "mercenary_items": sum(1 for i in items if i.container == "Mercenary"),
            "unique_items": sum(1 for i in items if i.quality == "Unique"),
            "set_items": sum(1 for i in items if i.quality == "Set"),
            "rare_items": sum(1 for i in items if i.quality == "Rare"),
            "runewords": sum(1 for i in items if i.quality == "Runeword"),
            "high_value_items": sum(1 for i in items if i.quality in ("Unique", "Set", "Runeword")),
        }
        recent = sorted(items, key=lambda i: i.created_at, reverse=True)[:5]
        stats["recently_added"] = [i.name for i in recent]
        return stats
