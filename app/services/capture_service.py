"""
D2R Vault — capture service.

Orchestrates the full F9 workflow (spec §6):
  screen capture -> tooltip detection -> crop -> preprocess -> OCR
  -> parse -> return a CaptureOutcome for the GUI to confirm/save.

This module composes the capture/ocr/parser layers but contains no
GUI code and no direct game interaction of any kind.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app import config
from app.capture.screen_capture import CaptureRegion, ScreenCapture
from app.capture.tooltip_detector import detect_tooltip_region
from app.ocr.ocr_engine import OCREngine, OCRResult
from app.parser.item_parser import ParsedItem, parse_item


@dataclass
class CaptureOutcome:
    parsed_item: ParsedItem
    ocr_result: OCRResult
    screenshot_path: str | None
    cropped_image: Image.Image
    low_confidence: bool


class CaptureService:
    def __init__(self, screen_capture: ScreenCapture, ocr_engine: OCREngine, settings: config.Settings):
        self.screen_capture = screen_capture
        self.ocr_engine = ocr_engine
        self.settings = settings

    def _save_screenshot(self, image: Image.Image) -> str | None:
        if not self.settings.save_screenshots:
            return None
        now = dt.datetime.now()
        folder = config.CAPTURES_DIR / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"capture_{now.strftime('%H%M%S_%f')}.png"
        path = folder / filename
        image.save(path)
        return str(path)

    def capture_and_parse(self) -> CaptureOutcome:
        mode = self.settings.tooltip_capture_mode
        full_shot = None
        if mode == "Automatic":
            full_shot = self.screen_capture.capture_full_screen()

        region_settings = {"fixed_region": self.settings.fixed_region}
        region: CaptureRegion = detect_tooltip_region(mode, full_shot, region_settings)

        cropped = full_shot.crop(
            (region.x, region.y, region.x + region.width, region.y + region.height)
        ) if full_shot is not None else self.screen_capture.capture(region)

        ocr_result = (
            self.ocr_engine.recognize_best_of(cropped)
            if hasattr(self.ocr_engine, "recognize_best_of")
            else self.ocr_engine.recognize(cropped)
        )

        parsed = parse_item(ocr_result.text, ocr_result.confidence)

        screenshot_path = self._save_screenshot(cropped)
        if screenshot_path:
            parsed.raw_ocr_text = ocr_result.text

        low_confidence = ocr_result.confidence < self.settings.ocr_confidence_threshold

        return CaptureOutcome(
            parsed_item=parsed,
            ocr_result=ocr_result,
            screenshot_path=screenshot_path,
            cropped_image=cropped,
            low_confidence=low_confidence,
        )
