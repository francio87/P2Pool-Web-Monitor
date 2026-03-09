from __future__ import annotations

import base64
from pathlib import Path


def build_embedded_font_face(font_path: Path) -> str:
    font_data = base64.b64encode(font_path.read_bytes()).decode("ascii")
    return (
        "@font-face {"
        "font-family:'Inter';"
        "font-style:normal;"
        "font-weight:100 900;"
        "font-display:swap;"
        "src:url(data:font/ttf;base64,"
        + font_data
        + ") format('truetype');"
        "}"
    )


def load_chart_js_inline(chart_js_path: Path) -> str:
    lines = chart_js_path.read_text(encoding="utf-8").splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if "sourceMappingURL" in stripped:
            continue
        if stripped.startswith("*") and ("http://" in stripped or "https://" in stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)
def ensure_static_dependencies(
    template_path: Path,
    ops_template_path: Path,
    chart_js_path: Path,
    inter_font_path: Path,
) -> None:
    if not template_path.exists():
        print(f"[X] Template file not found: {template_path}")
        print("Hint: use -h or --help to view configuration and examples.")
        raise SystemExit(1)
    if not ops_template_path.exists():
        print(f"[X] Ops template file not found: {ops_template_path}")
        print("Hint: use -h or --help to view configuration and examples.")
        raise SystemExit(1)
    if not chart_js_path.exists():
        print(f"[X] Local Chart.js file not found: {chart_js_path}")
        print("Cannot continue without local frontend dependencies.")
        print("Hint: use -h or --help to view configuration and examples.")
        raise SystemExit(1)
    if not inter_font_path.exists():
        print(f"[X] Local Inter font file not found: {inter_font_path}")
        print("Cannot continue without local embedded font dependency.")
        print("Hint: use -h or --help to view configuration and examples.")
        raise SystemExit(1)


def load_static_assets(chart_js_path: Path, inter_font_path: Path) -> tuple[str, str]:
    return load_chart_js_inline(chart_js_path), build_embedded_font_face(inter_font_path)
