from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from app.pipeline import analyze_file


APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = APP_ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Threat Modeling MVP (STRIDE)", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
    <h2>Threat Modeling MVP (STRIDE)</h2>
    <p>Use <a href="/docs">/docs</a> para enviar arquivos.</p>
    """


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    flows_json: str | None = Form(default=None),
) -> Any:
    """
    Analyze a diagram image or PDF and generate:
    - architecture.json (nodes/edges)
    - threats.json (STRIDE threats per node/edge)
    - report.html
    """
    raw = await file.read()

    flows: dict[str, Any] | None = None
    if flows_json:
        flows = json.loads(flows_json)

    result = analyze_file(
        filename=file.filename or "upload",
        content=raw,
        outputs_dir=OUTPUTS_DIR,
        flows_override=flows,
    )
    return JSONResponse(result)
