from __future__ import annotations

import argparse
from pathlib import Path

from app.pipeline import analyze_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Threat Modeling MVP - Analyze diagram (image or PDF).")
    parser.add_argument("--input", required=True, help="Path to input file (png/jpg/pdf).")
    parser.add_argument("--out", default="outputs", help="Output directory (default: outputs).")
    parser.add_argument(
        "--flows",
        default=None,
        help="Optional path to flows override JSON: { edges: [ {id, from, to, protocol?, data?}, ...] }",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    flows_override = None
    if args.flows:
        flows_override = __import__("json").loads(Path(args.flows).read_text(encoding="utf-8"))

    result = analyze_file(
        filename=in_path.name,
        content=in_path.read_bytes(),
        outputs_dir=out_dir,
        flows_override=flows_override,
    )

    print("Run:", result["run_id"])
    for k, v in result["artifacts"].items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
