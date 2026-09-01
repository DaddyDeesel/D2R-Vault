"""D2R Vault — tooltip region detection.

Automatic mode searches for a dense block of tooltip text in the captured D2R
client area. Fixed/Manual remain available for users who prefer an explicit
rectangle.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from app.capture.screen_capture import CaptureRegion


def detect_fixed_region(region_settings: dict) -> CaptureRegion:
    return CaptureRegion(x=region_settings.get("x", 0), y=region_settings.get("y", 0),
                         width=region_settings.get("width", 400), height=region_settings.get("height", 300))


def detect_automatic(full_screenshot: Image.Image, cursor_local: tuple[int, int] | None = None) -> CaptureRegion:
    """Locate a likely tooltip text block.

    We merge nearby high-contrast glyphs into text-block contours instead of
    treating each letter as a contour. Cursor proximity is a bonus because D2R
    tooltips are shown next to the item being hovered.
    """
    try:
        import cv2
    except ImportError:
        return _fallback_region(full_screenshot, cursor_local)

    rgb = np.array(full_screenshot.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    if w < 200 or h < 150:
        return CaptureRegion(0, 0, w, h)

    # D2R tooltip text is high-contrast against a very dark translucent panel.
    local = cv2.GaussianBlur(gray, (7, 7), 0)
    contrast = cv2.absdiff(gray, local)
    _, ink = cv2.threshold(contrast, 18, 255, cv2.THRESH_BINARY)
    # Merge letters -> words -> lines -> one tooltip-sized text block.
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((5, 17), np.uint8), iterations=1)
    ink = cv2.dilate(ink, np.ones((9, 19), np.uint8), iterations=2)

    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_score = float("-inf")
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw < 120 or ch < 35 or cw > w * 0.88 or ch > h * 0.90:
            continue
        area = cw * ch
        roi = gray[y:y+ch, x:x+cw]
        if roi.size == 0:
            continue
        # Prefer text-dense, darker regions and sensible tooltip geometry.
        darkness = max(0.0, 150.0 - float(np.mean(roi)))
        aspect_bonus = 30.0 if 0.55 <= (cw / max(ch, 1)) <= 7.0 else 0.0
        score = (area ** 0.5) + darkness * 1.7 + aspect_bonus
        if cursor_local:
            cx, cy = cursor_local
            bx, by = x + cw / 2, y + ch / 2
            dist = ((bx - cx) ** 2 + (by - cy) ** 2) ** 0.5
            score += max(0.0, 260.0 - dist * 0.20)
        if score > best_score:
            best, best_score = (x, y, cw, ch), score

    if best is None:
        return _fallback_region(full_screenshot, cursor_local)

    x, y, cw, ch = best
    pad_x, pad_y = 28, 24
    left, top = max(0, x-pad_x), max(0, y-pad_y)
    right, bottom = min(w, x+cw+pad_x), min(h, y+ch+pad_y)
    return CaptureRegion(left, top, right-left, bottom-top)


def _fallback_region(full_screenshot: Image.Image, cursor_local: tuple[int, int] | None = None) -> CaptureRegion:
    w, h = full_screenshot.size
    if cursor_local:
        cx, cy = cursor_local
        # Generous cursor-centered area, clipped to the D2R client. This is much
        # safer in windowed mode than using a desktop-centered rectangle.
        rw, rh = min(900, w), min(700, h)
        x = max(0, min(w-rw, cx-rw//2))
        y = max(0, min(h-rh, cy-rh//2))
        return CaptureRegion(x, y, rw, rh)
    return CaptureRegion(x=w//6, y=h//6, width=max(1, w*2//3), height=max(1, h*2//3))


def detect_tooltip_region(mode: str, full_screenshot: Image.Image | None, settings: dict,
                          cursor_local: tuple[int, int] | None = None) -> CaptureRegion:
    if mode in ("Fixed Region", "Manual Selection"):
        return detect_fixed_region(settings.get("fixed_region", {}))
    if mode == "Automatic" and full_screenshot is not None:
        return detect_automatic(full_screenshot, cursor_local=cursor_local)
    return detect_fixed_region(settings.get("fixed_region", {}))
