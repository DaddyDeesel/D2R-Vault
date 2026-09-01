"""
D2R Vault — repositories.

Thin, testable data-access layer between services and the ORM. Each
repository is intentionally simple: no business rules live here (those
belong in app/services/*), only queries and persistence.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    Character,
    GrailItem,
    Item,
    ItemDatabaseEntry,
    OCRCorrection,
)


class CharacterRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **fields) -> Character:
        char = Character(**fields)
        self.session.add(char)
        self.session.commit()
        self.session.refresh(char)
        return char

    def get(self, character_id: int) -> Character | None:
        return self.session.get(Character, character_id)

    def list_all(self) -> Sequence[Character]:
        return self.session.execute(
            select(Character).order_by(Character.name)
        ).scalars().all()

    def update(self, character_id: int, **fields) -> Character | None:
        char = self.get(character_id)
        if char is None:
            return None
        for key, value in fields.items():
            if hasattr(char, key):
                setattr(char, key, value)
        self.session.commit()
        self.session.refresh(char)
        return char

    def delete(self, character_id: int) -> bool:
        char = self.get(character_id)
        if char is None:
            return False
        self.session.delete(char)
        self.session.commit()
        return True


class ItemRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, item: Item) -> Item:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get(self, item_id: int) -> Item | None:
        return self.session.get(Item, item_id)

    def delete(self, item_id: int) -> bool:
        item = self.get(item_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.commit()
        return True

    def update(self, item_id: int, **fields) -> Item | None:
        item = self.get(item_id)
        if item is None:
            return None
        for key, value in fields.items():
            if hasattr(item, key):
                setattr(item, key, value)
        self.session.commit()
        self.session.refresh(item)
        return item

    def for_character(self, character_id: int, container: str | None = None) -> Sequence[Item]:
        stmt = select(Item).where(Item.character_id == character_id)
        if container:
            stmt = stmt.where(Item.container == container)
        return self.session.execute(stmt).scalars().all()

    def find_by_fingerprint(self, character_id: int, fingerprint: str) -> Item | None:
        stmt = select(Item).where(
            Item.character_id == character_id, Item.fingerprint == fingerprint
        )
        return self.session.execute(stmt).scalars().first()

    def all_favorites(self) -> Sequence[Item]:
        return self.session.execute(
            select(Item).where(Item.is_favorite.is_(True))
        ).scalars().all()

    def search(self, **criteria) -> Sequence[Item]:
        """Very small helper for exact-match search_service use; complex
        filtering is composed in app.services.search_service instead."""
        stmt = select(Item)
        for key, value in criteria.items():
            column = getattr(Item, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        return self.session.execute(stmt).scalars().all()

    def all(self) -> Sequence[Item]:
        return self.session.execute(select(Item)).scalars().all()


class ItemDatabaseRepository:
    """Read/write access to the local static reference DB (uniques, sets, etc.)."""

    def __init__(self, session: Session):
        self.session = session

    def bulk_insert(self, entries: Iterable[dict]) -> None:
        objs = [ItemDatabaseEntry(**e) for e in entries]
        self.session.add_all(objs)
        self.session.commit()

    def all(self, category: str | None = None) -> Sequence[ItemDatabaseEntry]:
        stmt = select(ItemDatabaseEntry)
        if category:
            stmt = stmt.where(ItemDatabaseEntry.category == category)
        return self.session.execute(stmt).scalars().all()

    def by_name_exact(self, name: str) -> ItemDatabaseEntry | None:
        stmt = select(ItemDatabaseEntry).where(ItemDatabaseEntry.name == name)
        return self.session.execute(stmt).scalars().first()


class OCRCorrectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def remember(self, ocr_text: str, corrected_text: str, item_id: int | None = None) -> OCRCorrection:
        row = OCRCorrection(ocr_text=ocr_text, corrected_text=corrected_text, item_id=item_id)
        self.session.add(row)
        self.session.commit()
        return row

    def lookup(self, ocr_text: str) -> str | None:
        stmt = select(OCRCorrection).where(OCRCorrection.ocr_text == ocr_text)
        row = self.session.execute(stmt).scalars().first()
        return row.corrected_text if row else None

    def all(self) -> Sequence[OCRCorrection]:
        return self.session.execute(select(OCRCorrection)).scalars().all()


class GrailRepository:
    def __init__(self, session: Session):
        self.session = session

    def is_discovered(self, reference_item_id: int) -> bool:
        stmt = select(GrailItem).where(GrailItem.reference_item_id == reference_item_id)
        return self.session.execute(stmt).scalars().first() is not None

    def record_discovery(self, reference_item_id: int, item_id: int | None) -> GrailItem:
        row = GrailItem(reference_item_id=reference_item_id, first_found_item_id=item_id)
        self.session.add(row)
        self.session.commit()
        return row

    def all(self) -> Sequence[GrailItem]:
        return self.session.execute(select(GrailItem)).scalars().all()
