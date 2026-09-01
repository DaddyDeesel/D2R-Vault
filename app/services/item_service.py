"""
D2R Vault — item service.

The glue between "a ParsedItem came out of OCR/manual entry" and "a
row exists in the items table": duplicate detection (spec §15) and
Holy Grail discovery tracking (spec §23) live here.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.models import Item
from app.database.repositories import GrailRepository, ItemDatabaseRepository, ItemRepository
from app.parser.item_parser import ParsedItem, compute_fingerprint


@dataclass
class SaveResult:
    item: Item | None
    is_duplicate: bool
    duplicate_of: Item | None = None
    is_new_grail_item: bool = False


class ItemService:
    def __init__(self, session: Session):
        self.session = session
        self.items = ItemRepository(session)
        self.reference = ItemDatabaseRepository(session)
        self.grail = GrailRepository(session)

    def _to_orm_fields(self, parsed: ParsedItem) -> dict:
        data = parsed.model_dump(exclude={"skills", "reference_item_name", "reference_match_score", "low_confidence_fields"})
        data["skills"] = [s.model_dump() for s in parsed.skills]
        return data

    def check_duplicate(self, character_id: int, parsed: ParsedItem) -> Item | None:
        fingerprint = compute_fingerprint(parsed)
        return self.items.find_by_fingerprint(character_id, fingerprint)

    def save_parsed_item(
        self, parsed: ParsedItem, character_id: int | None, container: str = "Inventory",
        x: int = 0, y: int = 0, width: int = 1, height: int = 1,
        force: bool = False, replace_item_id: int | None = None,
    ) -> SaveResult:
        fingerprint = compute_fingerprint(parsed)

        if character_id is not None and not force and replace_item_id is None:
            existing = self.items.find_by_fingerprint(character_id, fingerprint)
            if existing is not None:
                return SaveResult(item=None, is_duplicate=True, duplicate_of=existing)

        fields = self._to_orm_fields(parsed)
        fields.pop("extra_mods", None)
        fields["extra_mods"] = parsed.extra_mods

        if replace_item_id is not None:
            item = self.items.get(replace_item_id)
            if item is None:
                raise ValueError(f"Item {replace_item_id} not found for replace.")
            for k, v in fields.items():
                setattr(item, k, v)
            item.fingerprint = fingerprint
            item.character_id = character_id
            item.container = container
            item.x, item.y, item.width, item.height = x, y, width, height
            self.session.commit()
            self.session.refresh(item)
        else:
            item = Item(
                character_id=character_id, container=container, x=x, y=y, width=width, height=height,
                fingerprint=fingerprint, **fields,
            )
            item = self.items.add(item)

        is_new_grail = False
        if item.quality in ("Unique", "Set"):
            ref = self.reference.by_name_exact(item.name)
            if ref is not None:
                item.reference_item_id = ref.id
                self.session.commit()
                if not self.grail.is_discovered(ref.id):
                    self.grail.record_discovery(ref.id, item.id)
                    is_new_grail = True

        return SaveResult(item=item, is_duplicate=False, is_new_grail_item=is_new_grail)
