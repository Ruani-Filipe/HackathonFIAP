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
from app.vision.flow_detector import BaselineFlowDetector
from app.vision.io import bytes_to_image, image_to_bgr, is_pdf_bytes, pil_to_png_bytes
from app.vision.ocr import OcrConfig, ocr_bbox_text, ocr_full_text


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

    # OCR: fill node labels from diagram text when it's reliable enough.
    ocr_cfg = OcrConfig(enabled=True)

    def _looks_like_good_label(txt: str) -> bool:
        t = " ".join((txt or "").split()).strip()
        if not t:
            return False
        if len(t) < 4 or len(t) > 32:
            return False

        # Only allow letters/digits/spaces and a few safe separators
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -_/()")
        if any(ch not in allowed for ch in t):
            return False

        letters = sum(ch.isalpha() for ch in t)
        if letters < 4:
            return False

        # Discard OCR garbage: too few vowels among letters
        lt = "".join(ch.lower() for ch in t if ch.isalpha())
        if lt:
            vowels = sum(ch in "aeiou" for ch in lt)
            if vowels / max(len(lt), 1) < 0.28:
                return False

        # Require at least one "dictionary-ish" token used in architecture labels,
        # unless it's clearly TitleCase with >=2 words.
        kw = [
            "service",
            "database",
            "db",
            "api",
            "gateway",
            "server",
            "queue",
            "cache",
            "storage",
            "auth",
            "identity",
            "user",
            "client",
            "frontend",
            "backend",
            "worker",
            "lambda",
        ]
        tl = t.lower()
        has_kw = any(k in tl for k in kw)
        if not has_kw:
            # allow "Title Case" with >= 2 words (e.g., "Order Service")
            parts = t.split()
            if len(parts) < 2:
                return False
            if not all(p[:1].isupper() for p in parts if p):
                return False

        # avoid weird sequences
        if any(seq in tl for seq in ["iii", "lll", "___"]):
            return False

        return True

    # Fallback OCR: scan full page once to learn if common keywords exist in the diagram at all.
    # This helps decide whether to run more aggressive padding OCR and type inference.
    full_page_vocab: dict[str, set[str]] = {}
    for p in pages:
        try:
            full_txt = ocr_full_text(p.pil, ocr_cfg).lower()
        except Exception:
            full_txt = ""
        vocab = set()
        for k in [
            "service",
            "database",
            "db",
            "api",
            "gateway",
            "server",
            "queue",
            "cache",
            "storage",
            "auth",
            "identity",
            "user",
            "client",
        ]:
            if k in full_txt:
                vocab.add(k)
        full_page_vocab[p.name] = vocab

    for p in pages:
        bgr = image_to_bgr(p.pil)
        page_nodes = detector.detect(bgr=bgr, page_name=p.name)
        for i, n in enumerate(page_nodes, start=1):
            n["page"] = p.name

            # Fill label with OCR text (fallback to existing label if OCR is empty)
            bb = n.get("bbox") or {}
            if bb:
                if i == 1 or i % 25 == 0:
                    print(f"[OCR] page={p.name} node {i}/{len(page_nodes)} ...")

                # If the page has relevant words, allow bigger padding to capture labels near borders.
                pad = 18 if full_page_vocab.get(p.name) else 10
                txt = ocr_bbox_text(p.pil, bb, ocr_cfg, pad=pad)
                if _looks_like_good_label(txt):
                    n["label"] = txt

        nodes.extend(page_nodes)

    # 3) Flows (edges) - baseline heuristic extraction (optional)
    edges: list[dict[str, Any]] = []
    if flows_override and isinstance(flows_override.get("edges"), list):
        edges = flows_override["edges"]
    else:
        flow_detector = BaselineFlowDetector()
        for p in pages:
            bgr = image_to_bgr(p.pil)
            page_edges = flow_detector.detect_edges(bgr=bgr, nodes=nodes, page_name=p.name)
            for e in page_edges:
                e["page"] = p.name
            edges.extend(page_edges)

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
