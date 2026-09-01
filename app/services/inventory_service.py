"""
D2R Vault — inventory service.

Business rules for placing items in grid-based containers: collision
detection, free-slot discovery, and moving items between containers.
This never talks to Diablo II: Resurrected — it only manages the
database's own representation of a character's inventory (spec §33).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import GRID_SIZES
from app.database.models import Item
from app.database.repositories import ItemRepository


@dataclass
class GridCell:
    x: int
    y: int


class InventoryService:
    def __init__(self, session: Session):
        self.session = session
        self.items = ItemRepository(session)

    # -- collision / placement -------------------------------------------------

    def _occupied_cells(self, character_id: int, container: str, exclude_item_id: int | None = None) -> set[tuple[int, int]]:
        occupied: set[tuple[int, int]] = set()
        for item in self.items.for_character(character_id, container):
            if exclude_item_id is not None and item.id == exclude_item_id:
                continue
            for dx in range(item.width):
                for dy in range(item.height):
                    occupied.add((item.x + dx, item.y + dy))
        return occupied

    def can_place(
        self, character_id: int, container: str, x: int, y: int, width: int, height: int,
        exclude_item_id: int | None = None,
    ) -> bool:
        cols, rows = GRID_SIZES.get(container, (10, 4))
        if x < 0 or y < 0 or x + width > cols or y + height > rows:
            return False
        occupied = self._occupied_cells(character_id, container, exclude_item_id)
        for dx in range(width):
            for dy in range(height):
                if (x + dx, y + dy) in occupied:
                    return False
        return True

    def find_free_slot(self, character_id: int, container: str, width: int, height: int) -> tuple[int, int] | None:
        cols, rows = GRID_SIZES.get(container, (10, 4))
        for y in range(rows - height + 1):
            for x in range(cols - width + 1):
                if self.can_place(character_id, container, x, y, width, height):
                    return x, y
        return None

    def place_item(self, item: Item, container: str, x: int | None = None, y: int | None = None) -> Item:
        if x is None or y is None:
            slot = self.find_free_slot(item.character_id, container, item.width, item.height)
            if slot is None:
                raise ValueError(f"No free space in {container} for a {item.width}x{item.height} item.")
            x, y = slot
        elif not self.can_place(item.character_id, container, x, y, item.width, item.height, exclude_item_id=item.id):
            raise ValueError(f"Cannot place item at ({x}, {y}) in {container}: slot occupied or out of bounds.")

        item.container = container
        item.x, item.y = x, y
        self.session.commit()
        self.session.refresh(item)
        return item

    def move_item(self, item_id: int, container: str, x: int, y: int) -> Item:
        item = self.items.get(item_id)
        if item is None:
            raise ValueError(f"Item {item_id} not found.")
        return self.place_item(item, container, x, y)

    # -- optimizer ---------------------------------------------------------

    def free_slot_count(self, character_id: int, container: str) -> int:
        cols, rows = GRID_SIZES.get(container, (10, 4))
        occupied = self._occupied_cells(character_id, container)
        return cols * rows - len(occupied)

    def suggest_arrangement(self, character_id: int, container: str) -> dict:
        """A simple bin-packing heuristic: sort items largest-first and
        greedily place them from the top-left. Returns a preview
        (current vs. optimized free slot counts + a proposed placement
        map) without mutating the database — the caller applies it via
        `apply_arrangement` if the user confirms (spec §33: DB-only)."""
        cols, rows = GRID_SIZES.get(container, (10, 4))
        current_items = list(self.items.for_character(character_id, container))
        current_free = self.free_slot_count(character_id, container)

        ordered = sorted(current_items, key=lambda i: (i.width * i.height), reverse=True)
        occupied: set[tuple[int, int]] = set()
        placements: dict[int, tuple[int, int]] = {}

        for item in ordered:
            placed = False
            for y in range(rows - item.height + 1):
                for x in range(cols - item.width + 1):
                    cells = {(x + dx, y + dy) for dx in range(item.width) for dy in range(item.height)}
                    if cells.isdisjoint(occupied):
                        occupied |= cells
                        placements[item.id] = (x, y)
                        placed = True
                        break
                if placed:
                    break

        optimized_free = cols * rows - len(occupied)
        return {
            "current_free": current_free,
            "optimized_free": optimized_free,
            "placements": placements,
        }

    def apply_arrangement(self, container: str, placements: dict[int, tuple[int, int]]) -> None:
        for item_id, (x, y) in placements.items():
            item = self.items.get(item_id)
            if item is not None:
                item.x, item.y = x, y
                item.container = container
        self.session.commit()
