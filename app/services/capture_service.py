"""D2R Vault — capture service.

F9 workflow: capture -> tooltip detection -> OCR -> parse -> validate. Automatic
mode is foreground-window aware on Windows, so the same workflow works for D2R
fullscreen, borderless, and windowed modes.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from PIL import Image

from app import config
from app.capture.screen_capture import CaptureRegion, ScreenCapture
from app.capture.tooltip_detector import detect_tooltip_region
from app.ocr.ocr_engine import OCREngine, OCRResult
from app.parser.item_parser import ParsedItem, parse_item, validate_item_capture


class CaptureRejectedError(ValueError):
    """The screen was captured successfully, but it wasn't an item tooltip."""


@dataclass
class CaptureOutcome:
    parsed_item: ParsedItem
    ocr_result: OCRResult
    screenshot_path: str | None
    cropped_image: Image.Image
    low_confidence: bool
    evidence_score: int = 0


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
        path = folder / f"capture_{now.strftime('%H%M%S_%f')}.png"
        image.save(path)
        return str(path)

    def _automatic_source(self) -> tuple[Image.Image, tuple[int, int], tuple[int, int] | None]:
        """Return (image, screen-origin, cursor-local)."""
        if hasattr(self.screen_capture, "capture_foreground_window"):
            result = self.screen_capture.capture_foreground_window()
            if result:
                image, win_region = result
                cursor_local = None
                if hasattr(self.screen_capture, "get_cursor_position"):
                    pos = self.screen_capture.get_cursor_position()
                    if pos:
                        cursor_local = (pos[0] - win_region.x, pos[1] - win_region.y)
                return image, (win_region.x, win_region.y), cursor_local
        image = self.screen_capture.capture_full_screen()
        return image, (0, 0), None

    def capture_and_parse(self) -> CaptureOutcome:
        mode = self.settings.tooltip_capture_mode
        full_shot = None
        cursor_local = None
        if mode == "Automatic":
            full_shot, _origin, cursor_local = self._automatic_source()

        region_settings = {"fixed_region": self.settings.fixed_region}
        region: CaptureRegion = detect_tooltip_region(mode, full_shot, region_settings, cursor_local=cursor_local)
        cropped = (full_shot.crop((region.x, region.y, region.x+region.width, region.y+region.height))
                   if full_shot is not None else self.screen_capture.capture(region))

        ocr_result = (self.ocr_engine.recognize_best_of(cropped)
                      if hasattr(self.ocr_engine, "recognize_best_of") else self.ocr_engine.recognize(cropped))
        parsed = parse_item(ocr_result.text, ocr_result.confidence)
        valid, reason, evidence_score = validate_item_capture(parsed, ocr_result.text)
        if not valid:
            # Keep a rejected screenshot for debugging only when screenshot saving is enabled.
            self._save_screenshot(cropped)
            raise CaptureRejectedError(reason)

        screenshot_path = self._save_screenshot(cropped)
        parsed.raw_ocr_text = ocr_result.text
        low_confidence = ocr_result.confidence < self.settings.ocr_confidence_threshold
        return CaptureOutcome(parsed, ocr_result, screenshot_path, cropped, low_confidence, evidence_score)
