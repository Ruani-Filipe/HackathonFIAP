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
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        # Close gaps to connect box edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        nodes: list[dict[str, Any]] = []
        idx = 0

        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)

            area = cw * ch
            if area < 1500:
                continue

            # ignore huge background-like rectangles
            if cw > 0.95 * w and ch > 0.95 * h:
                continue

            # aspect ratio filter: keep somewhat box-like regions
            ar = cw / float(ch + 1e-6)
            if ar < 0.15 or ar > 8.0:
                continue

            # approx polygon for "rectangular-ish"
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.03 * peri, True)
            if len(approx) < 4:
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
