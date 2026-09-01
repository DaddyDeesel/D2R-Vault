import pytest

from app.parser.item_parser import parse_item
from app.services.backup_service import BackupService
from app.services.character_service import CharacterService
from app.services.inventory_service import InventoryService
from app.services.item_service import ItemService
from app.services.search_service import ItemFilter, SearchService, parse_natural_query


def test_create_character(session):
    svc = CharacterService(session)
    char = svc.create_character(name="FrozenOrb", char_class="Sorceress", level=90)
    assert char.id is not None
    assert char.name == "FrozenOrb"
    assert svc.list_characters() == [char]


def test_create_character_requires_name(session):
    svc = CharacterService(session)
    with pytest.raises(ValueError):
        svc.create_character(name="   ", char_class="Sorceress")


def test_item_save_and_duplicate_detection(session):
    char_svc = CharacterService(session)
    char = char_svc.create_character(name="Hammerdin", char_class="Paladin")

    item_svc = ItemService(session)
    parsed = parse_item(
        "Harlequin Crest\nShako\nDefense: 98\n+2 To All Skills\nUnique", ocr_confidence=95.0
    )

    result1 = item_svc.save_parsed_item(parsed, char.id, container="Personal Stash", x=0, y=0)
    assert result1.is_duplicate is False
    assert result1.item is not None

    result2 = item_svc.save_parsed_item(parsed, char.id, container="Personal Stash", x=1, y=0)
    assert result2.is_duplicate is True
    assert result2.duplicate_of.id == result1.item.id

    result3 = item_svc.save_parsed_item(parsed, char.id, container="Personal Stash", x=1, y=0, force=True)
    assert result3.is_duplicate is False


def test_inventory_placement_and_collision(session):
    char_svc = CharacterService(session)
    char = char_svc.create_character(name="Javazon", char_class="Amazon")
    item_svc = ItemService(session)
    inv_svc = InventoryService(session)

    parsed1 = parse_item("Sword\nDamage: 10-20", ocr_confidence=90.0)
    parsed2 = parse_item("Shield\nDefense: 50", ocr_confidence=90.0)

    r1 = item_svc.save_parsed_item(parsed1, char.id, container="Inventory", x=0, y=0)
    item1 = r1.item

    assert inv_svc.can_place(char.id, "Inventory", 0, 0, 1, 1) is False
    # When moving item1, its own occupied cells must be excluded from collision checks.
    assert inv_svc.can_place(char.id, "Inventory", 0, 0, 1, 1, exclude_item_id=item1.id) is True
    assert inv_svc.can_place(char.id, "Inventory", 1, 0, 1, 1) is True

    r2 = item_svc.save_parsed_item(parsed2, char.id, container="Inventory", x=1, y=0)
    item2 = r2.item

    with pytest.raises(ValueError):
        inv_svc.move_item(item2.id, "Inventory", 0, 0)  # occupied by item1

    moved = inv_svc.move_item(item2.id, "Inventory", 2, 0)
    assert (moved.x, moved.y) == (2, 0)


def test_search_service_filters(session):
    char_svc = CharacterService(session)
    char = char_svc.create_character(name="FCR Sorc", char_class="Sorceress")
    item_svc = ItemService(session)

    spirit = parse_item("Spirit\nRuneword\n+2 To All Skills\n35% Faster Cast Rate", ocr_confidence=90.0)
    item_svc.save_parsed_item(spirit, char.id, container="Inventory", x=0, y=0)

    sword = parse_item("Sword\nDamage: 10-20", ocr_confidence=90.0)
    item_svc.save_parsed_item(sword, char.id, container="Inventory", x=1, y=0)

    search = SearchService(session)
    results = search.search(ItemFilter(min_fcr=20))
    assert len(results) == 1
    assert results[0].name == "Spirit"

    nl_filter = parse_natural_query("Do I have a Spirit with at least 30 FCR?")
    assert nl_filter.min_fcr == 30
    nl_results = search.search(nl_filter)
    assert any(r.name == "Spirit" for r in nl_results)


def test_backup_service_creates_file(session, tmp_path):
    db_path = tmp_path / "d2r_vault.db"
    db_path.write_text("fake db contents")
    backup_dir = tmp_path / "backups"

    svc = BackupService(db_path=db_path, backup_dir=backup_dir)
    backup_path = svc.backup_now()

    assert backup_path is not None
    assert backup_path.exists()
    assert svc.list_backups() == [backup_path]
