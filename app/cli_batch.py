from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from app.pipeline import analyze_file

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


def _iter_images(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            files.append(p)
    return files


def _summarize_run(artifacts_dir: Path) -> dict[str, Any]:
    arch = json.loads((artifacts_dir / "architecture.json").read_text(encoding="utf-8"))
    threats = json.loads((artifacts_dir / "threats.json").read_text(encoding="utf-8"))

    nodes = arch.get("nodes", [])
    edges = arch.get("edges", [])
    labels = [n.get("label") for n in nodes if n.get("label") and n.get("label") != "component"]

    type_counts: dict[str, int] = {}
    for n in nodes:
        t = str(n.get("type") or "component")
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "run_id": arch.get("run_id"),
        "source": arch.get("source"),
        "nodes": len(nodes),
        "edges": len(edges),
        "threats": len(threats.get("items", [])),
        "ocr_labels_used": len(labels),
        "type_counts": type_counts,
        "report_html": str(artifacts_dir / "report.html"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch runner for architecture diagram analysis (MVP).")
    ap.add_argument("--input_dir", required=True, help="Folder containing images (recursive).")
    ap.add_argument("--out", default="outputs", help="Outputs folder (default: outputs).")
    ap.add_argument("--limit", type=int, default=10, help="Max number of images to process.")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for sampling.")
    ap.add_argument("--shuffle", action="store_true", help="Shuffle images before limiting.")
    args = ap.parse_args()

    in_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.out).resolve()

    if not in_dir.exists():
        raise SystemExit(f"input_dir not found: {in_dir}")

    images = _iter_images(in_dir)
    if not images:
        raise SystemExit(f"No images found under: {in_dir}")

    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(images)

    images = images[: max(1, args.limit)]

    summaries: list[dict[str, Any]] = []
    for img_path in images:
        data = img_path.read_bytes()
        res = analyze_file(filename=str(img_path), content=data, outputs_dir=out_dir)
        artifacts_dir = Path(res["artifacts"]["architecture_json"]).parent
        summaries.append(_summarize_run(artifacts_dir))

    batch_path = out_dir / "batch_summary.json"
    batch_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Processed {len(summaries)} images")
    print(f"Summary: {batch_path}")
    if summaries:
        print("Sample report:", summaries[0]["report_html"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
