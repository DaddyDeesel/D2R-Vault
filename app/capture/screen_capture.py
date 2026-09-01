"""D2R Vault — screen capture.

Uses external screen reading only. On Windows it can capture the foreground
window's *client area*, which makes Automatic mode work in both D2R fullscreen
and windowed/borderless modes without assuming a fixed desktop resolution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import os

from PIL import Image


@dataclass
class CaptureRegion:
    x: int
    y: int
    width: int
    height: int


class ScreenCapture(Protocol):
    def capture(self, region: CaptureRegion | None = None) -> Image.Image: ...
    def capture_full_screen(self) -> Image.Image: ...


class MSSScreenCapture:
    """Default implementation backed by mss, plus lightweight Win32 helpers."""

    def capture(self, region: CaptureRegion | None = None) -> Image.Image:
        import mss
        with mss.mss() as sct:
            if region is None:
                monitor = sct.monitors[1]
            else:
                monitor = {"left": region.x, "top": region.y, "width": region.width, "height": region.height}
            shot = sct.grab(monitor)
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def capture_full_screen(self) -> Image.Image:
        return self.capture(region=None)

    def get_foreground_window_region(self) -> CaptureRegion | None:
        """Return foreground client-area bounds in physical screen coordinates.

        Works for normal windowed, borderless, and exclusive/fullscreen-like
        D2R windows. Returns None outside Windows or if Win32 cannot resolve it.
        """
        if os.name != "nt":
            return None
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            class RECT(ctypes.Structure):
                _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                            ("right", wintypes.LONG), ("bottom", wintypes.LONG)]
            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            rect = RECT()
            if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
                return None
            tl = POINT(rect.left, rect.top)
            br = POINT(rect.right, rect.bottom)
            if not user32.ClientToScreen(hwnd, ctypes.byref(tl)) or not user32.ClientToScreen(hwnd, ctypes.byref(br)):
                return None
            width, height = br.x - tl.x, br.y - tl.y
            if width < 320 or height < 240:
                return None
            return CaptureRegion(tl.x, tl.y, width, height)
        except Exception:
            return None

    def get_cursor_position(self) -> tuple[int, int] | None:
        if os.name != "nt":
            return None
        try:
            import ctypes
            from ctypes import wintypes
            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
            pt = POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return pt.x, pt.y
        except Exception:
            pass
        return None

    def capture_foreground_window(self) -> tuple[Image.Image, CaptureRegion] | None:
        region = self.get_foreground_window_region()
        if region is None:
            return None
        return self.capture(region), region


class MockScreenCapture:
    def __init__(self, image: Image.Image):
        self._image = image

    def capture(self, region: CaptureRegion | None = None) -> Image.Image:
        if region is None:
            return self._image
        return self._image.crop((region.x, region.y, region.x + region.width, region.y + region.height))

    def capture_full_screen(self) -> Image.Image:
        return self._image
