from __future__ import annotations
from pathlib import Path

import cv2
from PIL import Image

from app.vision.baseline_detector import BaselineDetector
from app.vision.io import image_to_bgr


def main() -> None:
    img_path = Path(r"C:\Users\devru\OneDrive\Área de Trabalho\evidencia1.png")
    out_path = Path("outputs") / "_debug_evidencia1.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pil = Image.open(img_path)
    bgr = image_to_bgr(pil)

    det = BaselineDetector()
    nodes = det.detect(bgr=bgr, page_name="evidencia1")

    # Draw detected boxes
    for n in nodes:
        bb = n["bbox"]
        cv2.rectangle(bgr, (bb["x1"], bb["y1"]), (bb["x2"], bb["y2"]), (0, 0, 255), 2)
        cv2.putText(
            bgr,
            n["id"],
            (bb["x1"], max(0, bb["y1"] - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )

    cv2.imwrite(str(out_path), bgr)
    print("nodes=", len(nodes))
    print("debug_image=", out_path.resolve())


if __name__ == "__main__":
    main()
