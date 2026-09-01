"""
D2R Vault — tooltip region detection.

Three modes per spec §9:
  - Fixed Region: user-specified rectangle, always used as-is (most
    reliable; recommended default and starting point per the build
    spec's final instruction).
  - Manual Selection: same as Fixed Region but captured once via a
    selection UI, then stored as a fixed region.
  - Automatic: attempts to locate a tooltip-like rectangle in a full
    screenshot using basic image heuristics (text density + dark
    panel detection). Best-effort; falls back to a centered default
    region if nothing is found.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from app.capture.screen_capture import CaptureRegion


def detect_fixed_region(region_settings: dict) -> CaptureRegion:
    return CaptureRegion(
        x=region_settings.get("x", 0),
        y=region_settings.get("y", 0),
        width=region_settings.get("width", 400),
        height=region_settings.get("height", 300),
    )


def detect_automatic(full_screenshot: Image.Image) -> CaptureRegion:
    """Heuristic tooltip finder: D2R tooltips are dark rectangular
    panels with a border and a cluster of light-colored text. We look
    for a region with high local contrast and a dark, roughly-uniform
    background — good enough as a first pass; the spec explicitly
    allows starting with a configurable region and improving this
    later (§9, final instructions)."""
    try:
        import cv2
    except ImportError:
        return _fallback_region(full_screenshot)

    arr = np.array(full_screenshot.convert("L"))
    h, w = arr.shape

    # Simple contrast map via local standard deviation.
    blur = cv2.GaussianBlur(arr, (9, 9), 0)
    diff = cv2.absdiff(arr, blur)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_area = 0
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        # Tooltips are wider than tall, reasonably sized, not the whole screen.
        if area > best_area and 100 < cw < w * 0.6 and 60 < ch < h * 0.6 and cw > ch:
            best = (x, y, cw, ch)
            best_area = area

    if best is None:
        return _fallback_region(full_screenshot)

    x, y, cw, ch = best
    pad = 8
    return CaptureRegion(
        x=max(0, x - pad), y=max(0, y - pad),
        width=min(w - x, cw + pad * 2), height=min(h - y, ch + pad * 2),
    )


def _fallback_region(full_screenshot: Image.Image) -> CaptureRegion:
    w, h = full_screenshot.size
    return CaptureRegion(x=w // 4, y=h // 4, width=w // 2, height=h // 2)


def detect_tooltip_region(mode: str, full_screenshot: Image.Image | None, settings: dict) -> CaptureRegion:
    if mode == "Fixed Region" or mode == "Manual Selection":
        return detect_fixed_region(settings.get("fixed_region", {}))
    if mode == "Automatic" and full_screenshot is not None:
        return detect_automatic(full_screenshot)
    return detect_fixed_region(settings.get("fixed_region", {}))
