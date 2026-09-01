"""D2R Vault — OCR engine."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from PIL import Image
from app.ocr.image_processor import generate_ocr_candidates

@dataclass
class OCRResult:
    text: str
    confidence: float
    pass_name: str = "unknown"

class OCREngine(Protocol):
    def recognize(self, image: Image.Image) -> OCRResult: ...

class TesseractOCREngine:
    def __init__(self, language: str = "eng", tesseract_cmd: str | None = None):
        self.language = language
        self.tesseract_cmd = (tesseract_cmd or "").strip()

    def _configure(self):
        import pytesseract
        if self.tesseract_cmd:
            path = Path(self.tesseract_cmd)
            if not path.exists():
                raise RuntimeError(f"Tesseract executable not found: {path}")
            pytesseract.pytesseract.tesseract_cmd = str(path)
        elif shutil.which("tesseract") is None:
            # Common Windows install location gives a more useful first-run experience.
            common = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
            if common.exists():
                pytesseract.pytesseract.tesseract_cmd = str(common)
            else:
                raise RuntimeError(
                    "Tesseract OCR was not found. Install Tesseract or choose tesseract.exe in Settings → OCR."
                )
        return pytesseract

    def recognize(self, image: Image.Image) -> OCRResult:
        pytesseract = self._configure()
        data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
        confidences = []
        for i, word in enumerate(data.get("text", [])):
            if word.strip():
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
        best = None
        for pass_name, processed in generate_ocr_candidates(cropped_tooltip):
            result = self.recognize(processed)
            result.pass_name = pass_name
            if best is None or result.confidence > best.confidence:
                best = result
        return best if best is not None else OCRResult(text="", confidence=0.0)

class MockOCREngine:
    def __init__(self, canned_text: str, confidence: float = 95.0):
        self.canned_text = canned_text
        self.confidence = confidence
    def recognize(self, image: Image.Image) -> OCRResult:
        return OCRResult(text=self.canned_text, confidence=self.confidence, pass_name="mock")
    def recognize_best_of(self, cropped_tooltip: Image.Image) -> OCRResult:
        return self.recognize(cropped_tooltip)
