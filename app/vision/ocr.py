from __future__ import annotations

from dataclasses import dataclass

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


DEFAULT_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@dataclass(frozen=True)
class OcrConfig:
    enabled: bool = True
    tesseract_cmd: str = DEFAULT_TESSERACT_CMD
    lang: str = "eng"  # can be "por+eng" if language packs exist


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def ocr_bbox_text(pil: Image.Image, bbox: dict[str, int], config: OcrConfig, pad: int = 10) -> str:
    """Run OCR for the region defined by bbox on a PIL image."""
    if not config.enabled:
        return ""

    # Configure tesseract path (Windows)
    pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd

    w, h = pil.size
    x1 = _clamp(int(bbox["x1"]) - pad, 0, w)
    y1 = _clamp(int(bbox["y1"]) - pad, 0, h)
    x2 = _clamp(int(bbox["x2"]) + pad, 0, w)
    y2 = _clamp(int(bbox["y2"]) + pad, 0, h)

    if x2 <= x1 or y2 <= y1:
        return ""

    crop = pil.crop((x1, y1, x2, y2)).convert("RGB")

    # Strong OCR improvements for diagram labels:
    # - Upscale aggressively for small text
    # - Try multiple binarization strategies
    # - Try multiple PSM modes (single line / block)
    if crop.width < 420 or crop.height < 160:
        crop = crop.resize((crop.width * 3, crop.height * 3), resample=Image.Resampling.LANCZOS)

    gray = ImageOps.grayscale(crop)
    gray = ImageEnhance.Contrast(gray).enhance(2.6)
    gray = ImageEnhance.Sharpness(gray).enhance(1.8)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    # Two thresholds to handle different background styles
    bw1 = gray.point(lambda p: 255 if p > 165 else 0)
    bw2 = ImageOps.invert(gray).point(lambda p: 255 if p > 120 else 0)

    # OCR configs:
    # psm 7 = single line; psm 6 = block; psm 11 = sparse text
    # Keep whitelist but also allow ':' '.'
    wl = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:/_-()[] ."
    cfgs = [
        f"--psm 7 -c tessedit_char_whitelist={wl}",
        f"--psm 6 -c tessedit_char_whitelist={wl}",
        f"--psm 11 -c tessedit_char_whitelist={wl}",
    ]

    best = ""
    for img in (bw1, bw2):
        for cfg in cfgs:
            txt = pytesseract.image_to_string(img, lang=config.lang, config=cfg)
            txt = " ".join(txt.split()).strip()
            if len(txt) > len(best):
                best = txt

    return best


def ocr_full_text(pil: Image.Image, config: OcrConfig) -> str:
    """OCR the whole image (fallback) to extract a vocabulary of component keywords."""
    if not config.enabled:
        return ""
    pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd

    img = pil.convert("RGB")
    # scale up for better readability
    if img.width < 2200:
        scale = 2200 / float(img.width)
        img = img.resize((int(img.width * scale), int(img.height * scale)), resample=Image.Resampling.LANCZOS)

    gray = ImageOps.grayscale(img)
    gray = ImageEnhance.Contrast(gray).enhance(2.4)
    gray = ImageEnhance.Sharpness(gray).enhance(1.6)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    bw1 = gray.point(lambda p: 255 if p > 165 else 0)
    bw2 = ImageOps.invert(gray).point(lambda p: 255 if p > 120 else 0)

    wl = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:/_-()[] ."
    cfgs = [
        f"--psm 6 -c tessedit_char_whitelist={wl}",
        f"--psm 11 -c tessedit_char_whitelist={wl}",
    ]

    best = ""
    for img2 in (bw1, bw2):
        for cfg in cfgs:
            txt = pytesseract.image_to_string(img2, lang=config.lang, config=cfg)
            txt = " ".join(txt.split()).strip()
            if len(txt) > len(best):
                best = txt

    return best
