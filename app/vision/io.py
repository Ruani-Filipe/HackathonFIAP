from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image


def is_pdf_bytes(data: bytes) -> bool:
    return data[:4] == b"%PDF"


def bytes_to_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def pil_to_png_bytes(img: Image.Image) -> bytes:
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def image_to_bgr(img: Image.Image) -> np.ndarray:
    """
    Convert PIL image to OpenCV BGR ndarray.

    Important: some inputs are PNGs with alpha (RGBA). If we pass RGBA to
    cvtColor(RGB2BGR) it breaks or produces unexpected results, which can
    ruin edge detection. So we normalize to RGB first.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    rgb = np.array(img)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
