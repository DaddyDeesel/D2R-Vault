"""
D2R Vault — screen capture.

Pure external screen-reading: no window injection, no D2R process
interaction, no memory access. Uses `mss` for fast, cross-platform
screen grabs. Region is always caller-specified (from Settings' fixed
region, or a manual selection) — this module has no game-specific
knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass
class CaptureRegion:
    x: int
    y: int
    width: int
    height: int


class ScreenCapture(Protocol):
    """Interface so the capture backend can be swapped/mocked in tests."""

    def capture(self, region: CaptureRegion | None = None) -> Image.Image:
        ...

    def capture_full_screen(self) -> Image.Image:
        ...


class MSSScreenCapture:
    """Default implementation backed by the `mss` library."""

    def capture(self, region: CaptureRegion | None = None) -> Image.Image:
        import mss

        with mss.mss() as sct:
            if region is None:
                monitor = sct.monitors[1]
            else:
                monitor = {
                    "left": region.x, "top": region.y,
                    "width": region.width, "height": region.height,
                }
            shot = sct.grab(monitor)
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def capture_full_screen(self) -> Image.Image:
        return self.capture(region=None)


class MockScreenCapture:
    """Test double: returns a preset image instead of touching the real
    screen, so capture-pipeline logic can run in CI / headless envs."""

    def __init__(self, image: Image.Image):
        self._image = image

    def capture(self, region: CaptureRegion | None = None) -> Image.Image:
        if region is None:
            return self._image
        return self._image.crop((region.x, region.y, region.x + region.width, region.y + region.height))

    def capture_full_screen(self) -> Image.Image:
        return self._image
