from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from app.reporting import render_report_html, save_json
from app.stride import build_stride_threats
from app.vision.baseline_detector import BaselineDetector
from app.vision.io import bytes_to_image, image_to_bgr, is_pdf_bytes, pil_to_png_bytes


@dataclass(frozen=True)
class PageImage:
    page_index: int
    name: str
    pil: Image.Image


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _extract_images_from_pdf(pdf_bytes: bytes) -> list[PageImage]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PageImage] = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=200)  # render full page
        pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(PageImage(page_index=i, name=f"page_{i+1}", pil=pil))
    return pages


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def analyze_file(
    filename: str,
    content: bytes,
    outputs_dir: Path,
    flows_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    End-to-end MVP pipeline.
    Produces outputs under outputs_dir/<run_id>/...
    """
    run_id = f"{Path(filename).stem}_{_sha256(content)}"
    run_dir = outputs_dir / run_id
    _ensure_dir(run_dir)

    # 1) Ingest
    pages: list[PageImage]
    if is_pdf_bytes(content) or filename.lower().endswith(".pdf"):
        pages = _extract_images_from_pdf(content)
    else:
        pil = bytes_to_image(content)
        pages = [PageImage(page_index=0, name=Path(filename).stem or "image", pil=pil)]

    # Persist inputs
    inputs_dir = run_dir / "inputs"
    _ensure_dir(inputs_dir)
    for p in pages:
        (inputs_dir / f"{p.name}.png").write_bytes(pil_to_png_bytes(p.pil))

    # 2) Detect components (baseline heuristic detector)
    detector = BaselineDetector()
    nodes: list[dict[str, Any]] = []
    for p in pages:
        bgr = image_to_bgr(p.pil)
        page_nodes = detector.detect(bgr=bgr, page_name=p.name)
        for n in page_nodes:
            n["page"] = p.name
        nodes.extend(page_nodes)

    # 3) Flows (edges)
    # MVP: edges are optional. If provided, use override. Otherwise, create empty list.
    edges: list[dict[str, Any]] = []
    if flows_override and isinstance(flows_override.get("edges"), list):
        edges = flows_override["edges"]

    architecture = {"run_id": run_id, "source": filename, "nodes": nodes, "edges": edges}

    # 4) STRIDE threats
    threats = build_stride_threats(architecture)

    # 5) Save artifacts
    artifacts_dir = run_dir / "artifacts"
    _ensure_dir(artifacts_dir)

    arch_path = artifacts_dir / "architecture.json"
    threats_path = artifacts_dir / "threats.json"
    report_path = artifacts_dir / "report.html"

    save_json(arch_path, architecture)
    save_json(threats_path, threats)

    html = render_report_html(architecture=architecture, threats=threats)

    # Force UTF-8 encoding explicitly (avoid Windows default encodings).
    # Using write_bytes prevents any implicit encoding surprises.
    report_path.write_bytes(html.encode("utf-8"))

    return {
        "run_id": run_id,
        "artifacts": {
            "architecture_json": str(arch_path),
            "threats_json": str(threats_path),
            "report_html": str(report_path),
        },
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "threats": len(threats.get("items", [])),
        },
        "architecture": architecture,
        "threats": threats,
    }
