from app.parser.normalize import (
    best_fuzzy_match,
    normalize_ocr_text,
    normalize_whitespace,
    restore_letters_in_word,
)


def test_normalize_whitespace_collapses_blank_lines():
    raw = "Harlequin Crest\n\n\n\nShako   \n  Defense: 98  "
    result = normalize_whitespace(raw)
    assert "\n\n\n" not in result
    assert result.splitlines()[0] == "Harlequin Crest"
    assert result.splitlines()[-1] == "Defense: 98"


def test_normalize_ocr_text_strips_noise_chars():
    raw = "Harlequin| Crest\n+2 To^ All Skills"
    result = normalize_ocr_text(raw)
    assert "|" not in result
    assert "^" not in result


def test_best_fuzzy_match_corrects_typo():
    match, score = best_fuzzy_match("Harlequin Crsst", ["Harlequin Crest", "Shako", "Windforce"])
    assert match == "Harlequin Crest"
    assert score > 0.7


def test_best_fuzzy_match_returns_none_below_threshold():
    match, score = best_fuzzy_match("Totally Unrelated Gibberish", ["Harlequin Crest"])
    assert match is None


def test_restore_letters_does_not_touch_pure_digits():
    assert restore_letters_in_word("98") == "98"


def test_restore_letters_fixes_common_confusions():
    # "5haka" -> letters restored where the token is treated as name-like.
    assert restore_letters_in_word("5haka") == "Shaka"
