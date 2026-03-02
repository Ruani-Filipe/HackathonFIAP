from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    x1: int
    y1: int
    x2: int
    y2: int
    label: str
    score: float


class BaselineDetector:
    """
    Baseline heuristic detector:
    - Finds rectangular-ish contours as "components"
    - Classifies coarsely as "component"
    - Intended as fallback; a supervised detector (YOLO) should replace this.
    """

    def detect(self, bgr: np.ndarray, page_name: str) -> list[dict[str, Any]]:
        h, w = bgr.shape[:2]

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # --- Robust pre-processing (helps on screenshots / low-contrast diagrams) ---
        # Increase local contrast (CLAHE) + light denoise before edge detection.
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Prefer adaptive threshold for screenshots / diagrams with faint borders.
        thr = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
        )
        edges = cv2.Canny(thr, 30, 120)

        # Close gaps to connect box edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)

        # Extra dilation to help close broken rectangles
        closed = cv2.dilate(closed, kernel, iterations=1)

        # After closing/dilation, we want inner boxes too (not only the outermost contour).
        contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        nodes: list[dict[str, Any]] = []
        idx = 0

        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)

            area = cw * ch
            # Lower threshold to catch smaller boxes (common in screenshots)
            if area < 600:
                continue

            # ignore huge background-like rectangles (be more conservative)
            # Some screenshots have a full-page contour; treat anything covering most of the page as background.
            if cw > 0.80 * w and ch > 0.80 * h:
                continue

            # aspect ratio filter: keep somewhat box-like regions
            ar = cw / float(ch + 1e-6)
            if ar < 0.15 or ar > 8.0:
                continue

            # approx polygon for "rectangular-ish"
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)

            # If contour is too "line-like", skip. Otherwise accept even if it's not a perfect polygon.
            # Many diagrams have rounded corners or broken borders.
            if len(approx) < 3:
                continue

            idx += 1
            nodes.append(
                {
                    "id": f"{page_name}_n{idx}",
                    "type": "component",
                    "label": "component",
                    "score": 0.30,
                    "bbox": {"x1": int(x), "y1": int(y), "x2": int(x + cw), "y2": int(y + ch)},
                }
            )

        # If none detected, return empty list
        return nodes
