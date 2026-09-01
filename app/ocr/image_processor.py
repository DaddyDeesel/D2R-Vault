"""
D2R Vault — OCR image preprocessing pipeline (spec §8).

Produces multiple candidate variants of the same cropped tooltip so
the OCR engine can be run several times and the best result kept.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def to_grayscale(image: Image.Image) -> Image.Image:
    return image.convert("L")


def increase_contrast(image: Image.Image, factor: float = 1.8) -> Image.Image:
    return ImageEnhance.Contrast(image).enhance(factor)


def upscale(image: Image.Image, factor: float = 3.0) -> Image.Image:
    w, h = image.size
    return image.resize((int(w * factor), int(h * factor)), Image.LANCZOS)


def sharpen(image: Image.Image) -> Image.Image:
    return image.filter(ImageFilter.SHARPEN)


def threshold(image: Image.Image, level: int = 150) -> Image.Image:
    gray = image.convert("L")
    arr = np.array(gray)
    arr = np.where(arr > level, 255, 0).astype(np.uint8)
    return Image.fromarray(arr)


def pipeline_variant_original(image: Image.Image) -> Image.Image:
    """PASS 1: grayscale + contrast + upscale + sharpen (no thresholding)."""
    img = to_grayscale(image)
    img = increase_contrast(img, 1.5)
    img = upscale(img, 3.0)
    img = sharpen(img)
    return img


def pipeline_variant_high_contrast(image: Image.Image) -> Image.Image:
    """PASS 2: stronger contrast boost."""
    img = to_grayscale(image)
    img = increase_contrast(img, 2.4)
    img = upscale(img, 3.0)
    img = sharpen(img)
    return img


def pipeline_variant_thresholded(image: Image.Image) -> Image.Image:
    """PASS 3: binarized (black/white) version, good for clean UI fonts."""
    img = to_grayscale(image)
    img = increase_contrast(img, 2.0)
    img = upscale(img, 4.0)
    img = threshold(img, 150)
    return img


def generate_ocr_candidates(cropped_tooltip: Image.Image) -> list[tuple[str, Image.Image]]:
    """Returns a list of (pass_name, processed_image) tuples for the OCR
    engine to try, per spec §8's multi-pass design."""
    return [
        ("original", pipeline_variant_original(cropped_tooltip)),
        ("high_contrast", pipeline_variant_high_contrast(cropped_tooltip)),
        ("thresholded", pipeline_variant_thresholded(cropped_tooltip)),
    ]
