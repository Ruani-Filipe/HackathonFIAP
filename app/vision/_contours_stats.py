from __future__ import annotations

from pathlib import Path

import cv2
from PIL import Image

from app.vision.io import image_to_bgr


def main() -> None:
    p = Path(r"C:\Users\devru\OneDrive\Área de Trabalho\evidencia1.png")
    bgr = image_to_bgr(Image.open(p))

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thr = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )
    edges = cv2.Canny(thr, 30, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
    closed = cv2.dilate(closed, kernel, iterations=1)

    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print("contours=", len(cnts))

    areas = []
    ars = []
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        areas.append(cw * ch)
        ars.append(cw / float(ch + 1e-6))

    if areas:
        print("area_min=", min(areas), "area_max=", max(areas))
        print("ar_min=", min(ars), "ar_max=", max(ars))
    else:
        print("no contours after preprocessing")


if __name__ == "__main__":
    main()
