#!/usr/bin/env python3
"""Auditoría estática de reglas y umbrales del diagnóstico flexográfico."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

BASE_PATTERNS: Iterable[tuple[re.Pattern[str], str]] = (
    (re.compile(r"\\b4\\s*pt\\b", re.IGNORECASE), "Texto < 4 pt hardcodeado"),
    (re.compile(r"\\b0\\.?25\\s*pt\\b", re.IGNORECASE), "Trazo < 0.25 pt hardcodeado"),
    (re.compile(r"\\b3\\s*mm\\b", re.IGNORECASE), "Sangrado 3 mm hardcodeado"),
    (re.compile(r"\\b300\\s*dpi\\b", re.IGNORECASE), "Resolución 300 dpi hardcodeada"),
    (re.compile(r"\\b320\\s*%", re.IGNORECASE), "TAC 320% hardcodeado"),
)

LEGACY_SCALING = re.compile(r"clientWidth\s*/\s*imagen\.naturalWidth")

SKIP_FOLDERS = {"tests", "data", "tools", "__pycache__"}
SKIP_FILES = {"flexo_config.py"}
SCAN_EXTENSIONS = {".py", ".js", ".html"}


@dataclass
class Finding:
    file: str
    line: int
    detail: str
    pattern: str


def _should_scan(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return False
    if path.suffix not in SCAN_EXTENSIONS:
        return False
    for part in path.parts:
        if part in SKIP_FOLDERS and path.suffix != ".html":
            return False
    return True


def scan_for_patterns(root: Path) -> List[Finding]:
    hallazgos: List[Finding] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if not _should_scan(path):
            continue
        try:
            contenido = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for patron, descripcion in BASE_PATTERNS:
            for match in patron.finditer(contenido):
                line = contenido.count("\n", 0, match.start()) + 1
                hallazgos.append(
                    Finding(
                        file=str(path.relative_to(root)),
                        line=line,
                        detail=descripcion,
                        pattern=patron.pattern,
                    )
                )
        if LEGACY_SCALING.search(contenido):
            line = contenido.count("\n", 0, LEGACY_SCALING.search(contenido).start()) + 1
            hallazgos.append(
                Finding(
                    file=str(path.relative_to(root)),
                    line=line,
                    detail="Uso de clientWidth/naturalWidth detectado",
                    pattern=LEGACY_SCALING.pattern,
                )
            )
    return hallazgos


def run_checks(root: Path) -> Dict[str, List[Dict[str, str]]]:
    findings = scan_for_patterns(root)
    resultado: Dict[str, List[Dict[str, str]]] = {"hardcoded_values": [], "legacy_scaling": []}
    for item in findings:
        destino = (
            "legacy_scaling" if item.detail.startswith("Uso de clientWidth") else "hardcoded_values"
        )
        resultado[destino].append(
            {
                "file": item.file,
                "line": item.line,
                "detail": item.detail,
                "pattern": item.pattern,
            }
        )
    return resultado


def render_markdown(resultados: Dict[str, List[Dict[str, str]]]) -> str:
    lineas = ["# Informe de auditoría flexo", ""]
    if resultados["hardcoded_values"]:
        lineas.append("## Hardcodes de umbrales detectados")
        for finding in resultados["hardcoded_values"]:
            lineas.append(
                f"- `{finding['file']}` línea {finding['line']}: {finding['detail']} (patrón `{finding['pattern']}`)"
            )
    else:
        lineas.append("## Hardcodes de umbrales detectados")
        lineas.append("- ✅ Sin coincidencias")

    lineas.append("")
    if resultados["legacy_scaling"]:
        lineas.append("## Cálculos legacy de escalado UI")
        for finding in resultados["legacy_scaling"]:
            lineas.append(
                f"- `{finding['file']}` línea {finding['line']}: {finding['detail']}"
            )
    else:
        lineas.append("## Cálculos legacy de escalado UI")
        lineas.append("- ✅ Sin coincidencias")
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoría de diagnóstico flexo")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--format",
        choices={"json", "markdown"},
        default="json",
        help="Formato de salida",
    )
    args = parser.parse_args()
    resultados = run_checks(args.root)
    if args.format == "json":
        print(json.dumps(resultados, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(resultados))


if __name__ == "__main__":
    main()
