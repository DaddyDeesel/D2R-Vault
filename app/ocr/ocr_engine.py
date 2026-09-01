"""
D2R Vault — OCR engine.

Wraps Tesseract (via pytesseract) behind a small interface so it can
later be swapped for another OCR engine or an AI vision model (spec
§50 architecture requirement) without touching capture/parser code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image

from app.ocr.image_processor import generate_ocr_candidates


@dataclass
class OCRResult:
    text: str
    confidence: float  # 0-100
    pass_name: str = "unknown"


class OCREngine(Protocol):
    def recognize(self, image: Image.Image) -> OCRResult:
        ...


class TesseractOCREngine:
    def __init__(self, language: str = "eng"):
        self.language = language

    def recognize(self, image: Image.Image) -> OCRResult:
        import pytesseract

        data = pytesseract.image_to_data(
            image, lang=self.language, output_type=pytesseract.Output.DICT
        )
        words = []
        confidences = []
        for i, word in enumerate(data.get("text", [])):
            if word.strip():
                words.append(word)
                try:
                    conf = float(data["conf"][i])
                    if conf >= 0:
                        confidences.append(conf)
                except (ValueError, IndexError):
                    pass

        text = pytesseract.image_to_string(image, lang=self.language)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return OCRResult(text=text, confidence=avg_conf)

    def recognize_best_of(self, cropped_tooltip: Image.Image) -> OCRResult:
        """Runs all preprocessing passes (spec §8) and keeps the
        highest-confidence result."""
        candidates = generate_ocr_candidates(cropped_tooltip)
        best: OCRResult | None = None
        for pass_name, processed in candidates:
            result = self.recognize(processed)
            result.pass_name = pass_name
            if best is None or result.confidence > best.confidence:
                best = result
        return best if best is not None else OCRResult(text="", confidence=0.0)


class MockOCREngine:
    """Test double returning a canned result, so parser/service tests
    don't require Tesseract to be installed."""

    def __init__(self, canned_text: str, confidence: float = 95.0):
        self.canned_text = canned_text
        self.confidence = confidence

    def recognize(self, image: Image.Image) -> OCRResult:
        return OCRResult(text=self.canned_text, confidence=self.confidence, pass_name="mock")

    def recognize_best_of(self, cropped_tooltip: Image.Image) -> OCRResult:
        return self.recognize(cropped_tooltip)
