from __future__ import annotations

from pathlib import Path

import cv2
from PIL import Image

from app.vision.io import image_to_bgr


def main() -> None:
    img_path = Path(r"C:\Users\devru\OneDrive\Área de Trabalho\evidencia1.png")
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    pil = Image.open(img_path)
    bgr = image_to_bgr(pil)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Build a few variants to understand why contours are not found.
    variants: list[tuple[str, object]] = []

    # 1) Plain Canny
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges1 = cv2.Canny(blur, 30, 120)
    variants.append(("edges_canny_30_120", edges1))

    # 2) Adaptive threshold then edges
    thr = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )
    edges2 = cv2.Canny(thr, 30, 120)
    variants.append(("edges_adaptive_then_canny", edges2))

    # 3) Inverted adaptive threshold
    thr_inv = cv2.bitwise_not(thr)
    edges3 = cv2.Canny(thr_inv, 30, 120)
    variants.append(("edges_adaptive_inv_then_canny", edges3))

    # 4) Otsu threshold
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edges4 = cv2.Canny(otsu, 30, 120)
    variants.append(("edges_otsu_then_canny", edges4))

    # Save all
    for name, mat in variants:
        cv2.imwrite(str(out_dir / f"_debug_{name}.png"), mat)

    print("wrote:")
    for name, _ in variants:
        print((out_dir / f"_debug_{name}.png").resolve())


if __name__ == "__main__":
    main()
