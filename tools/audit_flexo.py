#!/usr/bin/env python3
"""Auditoría estática de reglas y umbrales del diagnóstico flexográfico."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

BASE_PATTERNS: Iterable[tuple[re.Pattern[str], str]] = (
    (re.compile(r"\\b3\\.?9\\s*pt\\b", re.IGNORECASE), "Texto 3.9 pt hardcodeado"),
    (re.compile(r"\\b4\\s*pt\\b", re.IGNORECASE), "Texto 4 pt hardcodeado"),
    (re.compile(r"\\b0\\.?24\\s*pt\\b", re.IGNORECASE), "Trazo 0.24 pt hardcodeado"),
    (re.compile(r"\\b0\\.?25\\s*pt\\b", re.IGNORECASE), "Trazo 0.25 pt hardcodeado"),
    (re.compile(r"\\b3\\s*mm\\b", re.IGNORECASE), "Sangrado 3 mm hardcodeado"),
    (re.compile(r"\\b2\\s*mm\\b", re.IGNORECASE), "Margen/borde 2 mm hardcodeado"),
    (re.compile(r"\\b300\\s*dpi\\b", re.IGNORECASE), "Resolución 300 dpi hardcodeada"),
    (re.compile(r"\\b600\\s*dpi\\b", re.IGNORECASE), "Resolución 600 dpi hardcodeada"),
    (re.compile(r"\\b280\\s*%", re.IGNORECASE), "TAC 280% hardcodeado"),
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


def _extract_dict_keys(text: str, marker: str) -> Set[str]:
    """Busca claves declaradas en un literal dict luego de ``marker``."""

    start = text.find(marker)
    if start == -1:
        return set()
    brace_level = 0
    keys: Set[str] = set()
    in_string = False
    quote_char = ''
    i = start + len(marker)
    while i < len(text):
        ch = text[i]
        if not in_string and ch in "{":
            brace_level += 1
            i += 1
            continue
        if brace_level == 0:
            break
        if ch in {'"', "'"}:
            if not in_string:
                in_string = True
                quote_char = ch
                key_start = i + 1
            elif quote_char == ch:
                key = text[key_start:i]
                if key:
                    keys.add(key)
                in_string = False
        if not in_string and ch == '}':
            brace_level -= 1
        i += 1
    return keys


def _collect_template_keys(text: str) -> Set[str]:
    keys = set(re.findall(r"diag\.get\('([A-Za-z0-9_]+)'", text))
    keys.update(re.findall(r"diagnosticoJson\.([A-Za-z0-9_]+)", text))
    return keys


def _collect_js_keys(text: str) -> Set[str]:
    return set(re.findall(r"diagnostico\.([A-Za-z0-9_]+)", text))


def find_try_except_pass(root: Path) -> List[Finding]:
    hallazgos: List[Finding] = []
    pattern = re.compile(r"except [^:]+:\s*(pass|\.\.\.|return None|return)")
    for path in root.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        try:
            contenido = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in pattern.finditer(contenido):
            line = contenido.count("\n", 0, match.start()) + 1
            hallazgos.append(
                Finding(
                    file=str(path.relative_to(root)),
                    line=line,
                    detail="Bloque except silencioso",
                    pattern=match.group(0),
                )
            )
    return hallazgos


def detect_duplicate_functions(root: Path) -> List[Finding]:
    hallazgos: List[Finding] = []
    bodies: Dict[str, Tuple[str, int, str]] = {}
    for path in root.rglob("*.py"):
        if path.suffix != ".py" or path.name == "__init__.py":
            continue
        if path.parts and any(part in SKIP_FOLDERS for part in path.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            module = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        for node in ast.walk(module):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                start = node.lineno - 1
                end = getattr(node, "end_lineno", node.lineno) - 1
                snippet = "\n".join(line.strip() for line in lines[start:end + 1])
                if len(snippet.splitlines()) < 3:
                    continue
                key = snippet
                if key in bodies:
                    prev_file, prev_line, prev_name = bodies[key]
                    hallazgos.append(
                        Finding(
                            file=str(path.relative_to(root)),
                            line=node.lineno,
                            detail=(
                                f"Duplicado de lógica con {prev_file}:{prev_line} (función {prev_name})"
                            ),
                            pattern=node.name,
                        )
                    )
                else:
                    bodies[key] = (str(path.relative_to(root)), node.lineno, node.name)
    return hallazgos


def run_checks(root: Path) -> Dict[str, List[Dict[str, str]]]:
    resultados: Dict[str, List[Dict[str, str]]] = {
        "hardcoded_values": [],
        "legacy_scaling": [],
        "silent_excepts": [],
        "duplicate_logic": [],
        "json_mismatch": [],
    }

    for item in scan_for_patterns(root):
        destino = (
            "legacy_scaling" if item.detail.startswith("Uso de clientWidth") else "hardcoded_values"
        )
        resultados[destino].append(
            {
                "file": item.file,
                "line": item.line,
                "detail": item.detail,
                "pattern": item.pattern,
            }
        )

    for item in find_try_except_pass(root):
        resultados["silent_excepts"].append(
            {
                "file": item.file,
                "line": item.line,
                "detail": item.detail,
                "pattern": item.pattern,
            }
        )

    for item in detect_duplicate_functions(root):
        resultados["duplicate_logic"].append(
            {
                "file": item.file,
                "line": item.line,
                "detail": item.detail,
                "pattern": item.pattern,
            }
        )

    # JSON keys
    try:
        routes_text = (root / "routes.py").read_text(encoding="utf-8")
        template_text = (root / "templates" / "resultado_flexo.html").read_text(encoding="utf-8")
        js_text = (root / "static" / "js" / "flexo_simulation.js").read_text(encoding="utf-8")
    except FileNotFoundError:
        routes_text = template_text = js_text = ""

    backend_keys = _extract_dict_keys(routes_text, "diagnostico_json = {")
    template_keys = _collect_template_keys(template_text)
    js_keys = _collect_js_keys(js_text)
    frontend_keys = template_keys | js_keys

    missing_in_front = sorted(k for k in backend_keys if k not in frontend_keys)
    missing_in_back = sorted(k for k in frontend_keys if k not in backend_keys)

    for key in missing_in_front:
        resultados["json_mismatch"].append(
            {
                "file": "routes.py",
                "line": 0,
                "detail": f"Clave '{key}' no utilizada en template/JS",
                "pattern": "diagnostico_json",
            }
        )
    for key in missing_in_back:
        resultados["json_mismatch"].append(
            {
                "file": "templates/resultado_flexo.html",
                "line": 0,
                "detail": f"Clave '{key}' usada en front pero no provista por backend",
                "pattern": "diagnostico_json",
            }
        )

    return resultados


def render_markdown(resultados: Dict[str, List[Dict[str, str]]]) -> str:
    lineas = ["# Informe de auditoría flexo", ""]

    def _seccion(titulo: str, clave: str) -> None:
        lineas.append(f"## {titulo}")
        hallazgos = resultados.get(clave, [])
        if hallazgos:
            for finding in hallazgos:
                lineas.append(
                    f"- `{finding['file']}` línea {finding['line']}: {finding['detail']}"
                )
        else:
            lineas.append("- ✅ Sin coincidencias")
        lineas.append("")

    _seccion("Hardcodes de umbrales detectados", "hardcoded_values")
    _seccion("Cálculos legacy de escalado UI", "legacy_scaling")
    _seccion("Bloques except silenciosos", "silent_excepts")
    _seccion("Duplicados de lógica", "duplicate_logic")
    _seccion("Desalineación de claves JSON", "json_mismatch")
    return "\n".join(lineas).strip()


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
