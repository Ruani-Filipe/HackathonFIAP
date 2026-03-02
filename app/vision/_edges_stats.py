from __future__ import annotations

from pathlib import Path

import cv2


def white_ratio(path: Path) -> float:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"Could not read: {path}")
    white = int((img > 0).sum())
    total = int(img.size)
    return white / total if total else 0.0


def main() -> None:
    files = [
        Path(r"outputs\_debug_edges_canny_30_120.png"),
        Path(r"outputs\_debug_edges_adaptive_then_canny.png"),
        Path(r"outputs\_debug_edges_adaptive_inv_then_canny.png"),
        Path(r"outputs\_debug_edges_otsu_then_canny.png"),
    ]
    for f in files:
        try:
            r = white_ratio(f)
            print(f"{f}: white_ratio={r:.4f}")
        except Exception as e:
            print(f"{f}: ERROR {e}")


if __name__ == "__main__":
    main()
