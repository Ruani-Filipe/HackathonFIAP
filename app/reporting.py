from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def render_report_html(architecture: dict[str, Any], threats: dict[str, Any]) -> str:
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("report.html.j2")

    # Avoid Jinja ambiguity with dict.items() method name by passing list explicitly.
    threat_items = threats.get("items", [])

    rendered = tpl.render(architecture=architecture, threats=threats, threat_items=threat_items)
    return rendered
