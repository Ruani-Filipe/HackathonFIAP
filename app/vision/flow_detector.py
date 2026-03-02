from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class EdgeCandidate:
    x1: int
    y1: int
    x2: int
    y2: int
    length: float


def _bbox_center(b: dict[str, int]) -> tuple[float, float]:
    return ((b["x1"] + b["x2"]) / 2.0, (b["y1"] + b["y2"]) / 2.0)


def _dist2(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def _closest_node_id(point: tuple[float, float], nodes: list[dict[str, Any]], page: str) -> str | None:
    best_id: str | None = None
    best_d = float("inf")
    for n in nodes:
        if n.get("page") != page:
            continue
        bb = n.get("bbox") or {}
        if not bb:
            continue
        c = _bbox_center(bb)
        d = _dist2(point, c)
        if d < best_d:
            best_d = d
            best_id = n.get("id")
    return best_id


class BaselineFlowDetector:
    """
    Baseline heuristic flow detector.
    Goal: generate a first approximation of edges between detected nodes
    from line segments (HoughLinesP).

    Limitations:
    - doesn't truly detect arrowheads (direction is approximated)
    - can create false positives on tables/grids
    - depends on diagram style/resolution
    """

    def detect_edges(
        self,
        bgr: np.ndarray,
        nodes: list[dict[str, Any]],
        page_name: str,
    ) -> list[dict[str, Any]]:
        h, w = bgr.shape[:2]

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Boost contrast and binarize to separate connectors from background
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)

        # Invert threshold tends to make dark lines become white on black
        thr = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 5
        )

        # Remove big filled blocks (components) to focus on thin connectors:
        # We approximate by eroding then dilating (opening) with a small kernel.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, kernel, iterations=1)

        edges = cv2.Canny(thr, 50, 150)

        # Hough line segments
        min_line_length = max(20, int(min(h, w) * 0.04))
        max_line_gap = max(5, int(min(h, w) * 0.01))

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180.0,
            threshold=60,
            minLineLength=min_line_length,
            maxLineGap=max_line_gap,
        )

        if lines is None:
            return []

        # Convert to candidates and filter very short ones
        candidates: list[EdgeCandidate] = []
        for l in lines:
            x1, y1, x2, y2 = [int(v) for v in l[0]]
            length = float(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
            if length < min_line_length:
                continue
            candidates.append(EdgeCandidate(x1=x1, y1=y1, x2=x2, y2=y2, length=length))

        # Map line endpoints to nearest nodes (by center distance).
        edges_out: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        eid = 0

        for c in candidates:
            p1 = (float(c.x1), float(c.y1))
            p2 = (float(c.x2), float(c.y2))

            n1 = _closest_node_id(p1, nodes, page_name)
            n2 = _closest_node_id(p2, nodes, page_name)

            if not n1 or not n2 or n1 == n2:
                continue

            # Deduplicate
            key = (n1, n2)
            if key in seen:
                continue
            seen.add(key)

            eid += 1
            edges_out.append(
                {
                    "id": f"{page_name}_e{eid}",
                    "type": "flow",
                    "source": n1,
                    "target": n2,
                    "score": 0.20,
                    "bbox": {
                        "x1": int(min(c.x1, c.x2)),
                        "y1": int(min(c.y1, c.y2)),
                        "x2": int(max(c.x1, c.x2)),
                        "y2": int(max(c.y1, c.y2)),
                    },
                }
            )

        return edges_out
