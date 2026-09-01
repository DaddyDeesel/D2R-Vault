"""
D2R Vault — OCR text normalization and fuzzy matching helpers.

This module has no dependency on the GUI, database, or capture layers,
and only optionally depends on RapidFuzz (falling back to stdlib
difflib if it isn't installed), so it can be developed and unit-tested
in isolation from everything else — including on machines without
Diablo II: Resurrected or Tesseract installed.
"""
from __future__ import annotations

import re

try:
    from rapidfuzz import fuzz as _rf_fuzz

    def _similarity(a: str, b: str) -> float:
        return _rf_fuzz.ratio(a, b) / 100.0

except ImportError:  # pragma: no cover - exercised only when rapidfuzz absent
    from difflib import SequenceMatcher

    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()


# Common OCR confusions seen on D2R's tooltip font. Applied selectively
# (see `restore_letters_in_word`) — never blindly substituted into
# strings that are supposed to be numeric, so real stat values aren't
# corrupted (spec §52).
LETTER_SUBSTITUTIONS = {
    "0": "O",
    "1": "I",
    "5": "S",
    "8": "B",
    "6": "G",
}

_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{2,}")
_PUNCT_NOISE_RE = re.compile(r"[|_`~^]")


def normalize_whitespace(text: str) -> str:
    """Collapse repeated spaces/tabs, trim each line, and collapse blank
    line runs, without destroying intentional line breaks (each usually
    corresponds to a distinct tooltip stat)."""
    lines = [
        _WHITESPACE_RE.sub(" ", line).strip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    joined = "\n".join(lines)
    joined = _MULTI_NEWLINE_RE.sub("\n", joined)
    return joined.strip()


def strip_punctuation_noise(text: str) -> str:
    """Remove stray OCR artifacts that are never legitimate tooltip
    characters (pipes, underscores, backticks, carets)."""
    return _PUNCT_NOISE_RE.sub("", text)


def normalize_ocr_text(text: str) -> str:
    """Full normalization pipeline applied to raw OCR output before
    parsing: whitespace, punctuation noise, capitalization is left
    intact (item names are case-sensitive-ish, quality flags use it)."""
    text = strip_punctuation_noise(text)
    text = normalize_whitespace(text)
    return text


def restore_letters_in_word(word: str) -> str:
    """Given a word-like token that should be alphabetic (e.g. an item
    name token), replace common digit/letter confusions. This is only
    ever applied to tokens already identified as "name-like" by the
    caller — never to numeric stat tokens, so legitimate numbers are
    never corrupted."""
    if word.isdigit():
        return word
    return "".join(LETTER_SUBSTITUTIONS.get(ch, ch) for ch in word)


def best_fuzzy_match(candidate: str, choices: list[str], threshold: float = 0.72) -> tuple[str | None, float]:
    """Return (best_match, score 0..1) or (None, 0.0) if nothing clears
    the threshold. Case-insensitive."""
    if not candidate or not choices:
        return None, 0.0

    candidate_norm = candidate.strip().lower()
    best_choice = None
    best_score = 0.0
    for choice in choices:
        score = _similarity(candidate_norm, choice.strip().lower())
        if score > best_score:
            best_score = score
            best_choice = choice

    if best_score >= threshold:
        return best_choice, best_score
    return None, best_score
