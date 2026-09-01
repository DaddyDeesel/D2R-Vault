"""D2R Vault — export service (spec §30)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.models import Item
from app.database.repositories import ItemRepository

EXPORT_COLUMNS = [
    "Character", "Container", "Item", "Base", "Quality", "Level",
    "Ethereal", "Sockets", "Defense", "Damage", "FCR", "FHR", "MF",
    "Resistances", "Skills", "Date Added",
]


def _row_for_item(item: Item) -> dict:
    damage = f"{item.damage_min}-{item.damage_max}" if item.damage_min is not None else ""
    resist = ", ".join(f"{k}:{v}" for k, v in (item.resistances or {}).items())
    skills = ", ".join(f"+{s.get('amount')} {s.get('skill')}" for s in (item.skills or []))
    return {
        "Character": item.character.name if item.character else "",
        "Container": item.container,
        "Item": item.name,
        "Base": item.base_name or "",
        "Quality": item.quality,
        "Level": item.required_level or "",
        "Ethereal": "Yes" if item.ethereal else "No",
        "Sockets": item.socket_count,
        "Defense": item.defense or "",
        "Damage": damage,
        "FCR": item.faster_cast_rate or "",
        "FHR": item.faster_hit_recovery or "",
        "MF": item.magic_find or "",
        "Resistances": resist,
        "Skills": skills,
        "Date Added": item.created_at.isoformat() if item.created_at else "",
    }


class ExportService:
    def __init__(self, session: Session):
        self.items = ItemRepository(session)

    def _rows(self, character_id: int | None = None) -> list[dict]:
        items = self.items.for_character(character_id) if character_id else self.items.all()
        return [_row_for_item(i) for i in items]

    def export_csv(self, path: Path, character_id: int | None = None) -> Path:
        rows = self._rows(character_id)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def export_json(self, path: Path, character_id: int | None = None) -> Path:
        rows = self._rows(character_id)
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return path

    def export_excel(self, path: Path, character_id: int | None = None) -> Path:
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise RuntimeError(
                "Excel export requires the 'openpyxl' package (pip install openpyxl)."
            ) from exc

        rows = self._rows(character_id)
        wb = Workbook()
        ws = wb.active
        ws.title = "Inventory"
        ws.append(EXPORT_COLUMNS)
        for row in rows:
            ws.append([row.get(col, "") for col in EXPORT_COLUMNS])
        wb.save(path)
        return path
