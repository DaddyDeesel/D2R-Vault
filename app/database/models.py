"""
D2R Vault — SQLAlchemy ORM models.

Structured, queryable tables rather than one giant JSON blob (see spec
§28). `extra_mods` on Item is the *only* JSON column, reserved for
mod-specific/unusual properties so information from OCR is never lost
even if it doesn't map to a named column.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    char_class: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    difficulty: Mapped[str] = mapped_column(String(16), default="Normal")
    season: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hardcore: Mapped[bool] = mapped_column(Boolean, default=False)
    ladder: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    items: Mapped[list["Item"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    builds: Mapped[list["Build"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id"), nullable=True
    )

    # Placement
    container: Mapped[str] = mapped_column(String(32), default="Inventory")
    x: Mapped[int] = mapped_column(Integer, default=0)
    y: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=1)
    height: Mapped[int] = mapped_column(Integer, default=1)
    equipment_slot: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Identity
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quality: Mapped[str] = mapped_column(String(32), default="Normal")
    item_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    identified: Mapped[bool] = mapped_column(Boolean, default=True)
    ethereal: Mapped[bool] = mapped_column(Boolean, default=False)
    socket_count: Mapped[int] = mapped_column(Integer, default=0)

    # Requirements
    required_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_strength: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_dexterity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Core combat stats
    defense: Mapped[int | None] = mapped_column(Integer, nullable=True)
    damage_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    damage_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    durability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    enhanced_damage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enhanced_defense: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Attributes
    strength: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dexterity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vitality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    life: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mana: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Resistances (JSON: {"fire": 30, "cold": 30, "lightning": 0, "poison": 0})
    resistances: Mapped[dict] = mapped_column(JSON, default=dict)
    all_resistances: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Skills (JSON list of {"skill": "Fire Ball", "amount": 3, "tab": "Sorceress"})
    skills: Mapped[list] = mapped_column(JSON, default=list)
    plus_to_skills: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Utility / QoL mods
    faster_cast_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    faster_hit_recovery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    faster_run_walk: Mapped[int | None] = mapped_column(Integer, nullable=True)
    life_leech: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mana_leech: Mapped[int | None] = mapped_column(Integer, nullable=True)
    magic_find: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gold_find: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crushing_blow: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadly_strike: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_wounds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Roll tracking (JSON: {"stat": "magic_find", "value": 50, "min": 25, "max": 50})
    rolls: Mapped[list] = mapped_column(JSON, default=list)

    # Catch-all for anything OCR captured that doesn't map to a column above.
    extra_mods: Mapped[dict] = mapped_column(JSON, default=dict)

    # Reference-DB linkage (fuzzy-matched separately from raw OCR text)
    reference_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_database.id"), nullable=True
    )

    # Provenance / trust
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # User-added metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    estimated_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trade_status: Mapped[str] = mapped_column(String(16), default="Unknown")
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    character: Mapped["Character | None"] = relationship(back_populates="items")
    reference: Mapped["ItemDatabaseEntry | None"] = relationship()


class ItemDatabaseEntry(Base):
    """Local static reference DB: base items, uniques, sets, runewords, etc."""

    __tablename__ = "item_database"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    # category in {base, unique, set, rune, runeword, gem, jewel, charm}
    base_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    required_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fixed_stats: Mapped[list] = mapped_column(JSON, default=list)
    variable_stats: Mapped[list] = mapped_column(JSON, default=list)
    icon_path: Mapped[str | None] = mapped_column(String(512), nullable=True)


class OCRCorrection(Base):
    __tablename__ = "ocr_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ocr_text: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    corrected_text: Mapped[str] = mapped_column(String(256), nullable=False)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class Capture(Base):
    """A raw F9 capture event, kept independent of whether it became an Item."""

    __tablename__ = "captures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    parse_succeeded: Mapped[bool] = mapped_column(Boolean, default=False)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    build_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    character: Mapped["Character"] = relationship(back_populates="builds")
    build_items: Mapped[list["BuildItem"]] = relationship(
        back_populates="build", cascade="all, delete-orphan"
    )


class BuildItem(Base):
    __tablename__ = "build_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("builds.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    slot: Mapped[str | None] = mapped_column(String(16), nullable=True)

    build: Mapped["Build"] = relationship(back_populates="build_items")
    item: Mapped["Item"] = relationship()


class Wishlist(Base):
    __tablename__ = "wishlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    wishlist_items: Mapped[list["WishlistItem"]] = relationship(
        back_populates="wishlist", cascade="all, delete-orphan"
    )


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wishlist_id: Mapped[int] = mapped_column(ForeignKey("wishlists.id"))
    item_name: Mapped[str] = mapped_column(String(128), nullable=False)
    fulfilled_by_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id"), nullable=True
    )

    wishlist: Mapped["Wishlist"] = relationship(back_populates="wishlist_items")
    fulfilled_by: Mapped["Item | None"] = relationship()


class GrailItem(Base):
    """Tracks discovery of each unique/set item in the reference DB, once ever."""

    __tablename__ = "grail_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_item_id: Mapped[int] = mapped_column(
        ForeignKey("item_database.id"), unique=True
    )
    first_found_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id"), nullable=True
    )
    discovered_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    __table_args__ = (UniqueConstraint("reference_item_id", name="uq_grail_ref"),)


class Setting(Base):
    """Key/value fallback store for settings not modeled elsewhere (rarely used;
    primary settings live in data/settings.json via app.config.Settings)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)


class SchemaVersion(Base):
    __tablename__ = "schema_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


CURRENT_SCHEMA_VERSION = 1
