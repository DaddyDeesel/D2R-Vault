from app.parser.item_parser import compute_fingerprint, parse_item

HARLEQUIN_OCR = """Harlequin Crest
Shako
Defense: 98
+2 To All Skills
+1 To All Attributes
+50% Enhanced Defense
Damage Reduced By 10%
+5% To Maximum Life
+5% To Maximum Mana
Unique"""

HARLEQUIN_OCR_NOISY = """Harlequin Crsst
Shako
Defense: 98
+2 To All Skils
+1 To All Attributes
+50% Enhanced Defense
Damage Reduced By 10%
Unique"""


def test_parse_item_detects_name_quality_and_stats():
    parsed = parse_item(HARLEQUIN_OCR, ocr_confidence=94.0)
    assert parsed.name == "Harlequin Crest"
    assert parsed.base_name == "Shako"
    assert parsed.quality == "Unique"
    assert parsed.defense == 98
    assert parsed.plus_to_skills == 2
    assert parsed.enhanced_defense == 50


def test_parse_item_tolerates_ocr_noise():
    parsed = parse_item(HARLEQUIN_OCR_NOISY, ocr_confidence=61.0)
    # Fuzzy match should still resolve to the correct canonical name.
    assert parsed.name == "Harlequin Crest"
    assert parsed.defense == 98


def test_parse_item_never_raises_on_garbage():
    parsed = parse_item("", ocr_confidence=0.0)
    assert parsed.name  # falls back to something rather than crashing
    parsed2 = parse_item("!!!@@@###\n\n\n???", ocr_confidence=5.0)
    assert parsed2.raw_ocr_text != "" or parsed2.name


def test_fingerprint_is_stable_for_identical_items():
    a = parse_item(HARLEQUIN_OCR, ocr_confidence=94.0)
    b = parse_item(HARLEQUIN_OCR, ocr_confidence=88.0)  # confidence shouldn't matter
    assert compute_fingerprint(a) == compute_fingerprint(b)


def test_fingerprint_differs_for_different_items():
    a = parse_item(HARLEQUIN_OCR, ocr_confidence=94.0)
    b = parse_item("Stone of Jordan\n+1 To All Skills\n+20 To Mana\nUnique", ocr_confidence=90.0)
    assert compute_fingerprint(a) != compute_fingerprint(b)


def test_resistances_parsed_into_dict():
    ocr = "Spirit\nRuneword\n+2 To All Skills\nFire Resist +30%\nCold Resist +30%"
    parsed = parse_item(ocr)
    assert parsed.resistances.get("fire") == 30
    assert parsed.resistances.get("cold") == 30


def test_skills_list_populated():
    ocr = "Nightwing's Veil\nSpired Helm\n+2 To Necromancer Skill Levels\n+2 To Curses"
    parsed = parse_item(ocr)
    assert any(s.skill.lower() == "curses" for s in parsed.skills)


def test_ui_stash_tab_gems_is_rejected_as_item_capture():
    from app.parser.item_parser import validate_item_capture
    parsed = parse_item("Gems", ocr_confidence=98.0)
    valid, reason, score = validate_item_capture(parsed, "Gems")
    assert not valid
    assert "label" in reason.lower() or "tooltip" in reason.lower()


def test_real_gem_tooltip_is_not_confused_with_gems_tab():
    from app.parser.item_parser import validate_item_capture
    text = """Perfect Topaz\nCan be Inserted into Socketed Items\nWeapons: Adds 1-40 Lightning Damage\nArmor: 24% Better Chance of Getting Magic Items\nShields: Lightning Resist +40%"""
    parsed = parse_item(text, ocr_confidence=92.0)
    valid, reason, score = validate_item_capture(parsed, text)
    assert valid, reason
    assert score >= 2
