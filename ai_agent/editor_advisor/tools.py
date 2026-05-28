from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_READ_FILES = {
    "AGENTS.md",
    "requirements.txt",
    "app.py",
    "routes.py",
    "DOCS/OFFSET/00_CONTEXTO_OFFSET.md",
    "DOCS/OFFSET/01_MAPA_EDITOR_VISUAL.md",
    "DOCS/OFFSET/02_ESTADO_OFFSET.md",
    "DOCS/OFFSET/03_AUDITORIA_OFFSET.md",
    "DOCS/OFFSET/04_PLAN_OFFSET.md",
    "DOCS/OFFSET/05_DIARIO_OFFSET.md",
    "DOCS/OFFSET/06_CONTRATO_LAYOUT.md",
    "DOCS/OFFSET/07_CONTRATO_SLOTS.md",
    "DOCS/OFFSET/08_VALIDACION_SALIDA.md",
    "DOCS/OFFSET/09_VALIDACION_GEOMETRICA.md",
    "DOCS/OFFSET/10_INDICADOR_DISTANCIA_UTIL.md",
    "DOCS/OFFSET/11_HERRAMIENTAS_EDICION_PRO.md",
    "DOCS/OFFSET/12_STEP_REPEAT_INTELIGENTE.md",
    "DOCS/OFFSET/13_SIMULADOR_CUADERNILLOS.md",
    "DOCS/OFFSET/14_MAPA_FUNCIONAL_EDITOR_VISUAL_IA.md",
    "templates/editor_offset_visual.html",
    "static/js/editor_offset_visual.js",
    "static/css/editor_offset_visual.css",
    "engines/step_repeat_pro_engine.py",
    "engines/nesting_pro_engine.py",
    "services/editor_offset_imposition_service.py",
    "services/editor_offset_jobs.py",
    "services/editor_offset_layout_defaults.py",
    "services/editor_offset_output_contract.py",
    "services/editor_offset_uploads.py",
    "montaje_offset_inteligente.py",
    "cuadernillos/simulator.py",
}

ALLOWED_SEARCH_ROOTS = {
    "AGENTS.md",
    "requirements.txt",
    "app.py",
    "routes.py",
    "DOCS/OFFSET",
    "ai_agent",
    "cuadernillos",
    "engines",
    "montaje_offset_inteligente.py",
    "services",
    "strategies",
    "templates",
    "static/js",
    "static/css",
    "tests",
}

BLOCKED_PARTS = {
    ".env",
    ".git",
    ".pytest_cache",
    "__pycache__",
    "venv",
    "output",
    "output_flexo",
    "preview_temp",
    "static/constructor_offset_jobs",
    "static/uploads",
    "static/outputs",
    "static/previews",
}


def _repo_root(repo_root: str | Path | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root else REPO_ROOT


def _to_posix(path: Path) -> str:
    return path.as_posix()


def _relative_path(path: str | Path, repo_root: str | Path | None = None) -> str:
    root = _repo_root(repo_root)
    candidate = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    try:
        rel = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("La ruta solicitada esta fuera del repositorio.") from exc
    rel_posix = _to_posix(rel)
    if _is_blocked(rel_posix):
        raise ValueError("La ruta solicitada esta bloqueada para el agente asesor.")
    return rel_posix


def _is_blocked(rel_posix: str) -> bool:
    parts = rel_posix.split("/")
    if rel_posix in BLOCKED_PARTS:
        return True
    if parts and parts[0] in BLOCKED_PARTS:
        return True
    return any(rel_posix == item or rel_posix.startswith(f"{item}/") for item in BLOCKED_PARTS)


def _is_allowed_file(rel_posix: str) -> bool:
    return rel_posix in ALLOWED_READ_FILES


def _allowed_search_targets(query_paths: Iterable[str] | None, repo_root: str | Path | None = None) -> List[str]:
    targets = list(query_paths or ALLOWED_SEARCH_ROOTS)
    allowed = []
    for target in targets:
        rel = _relative_path(target, repo_root)
        if _is_blocked(rel):
            continue
        if rel in ALLOWED_SEARCH_ROOTS or any(rel.startswith(f"{root}/") for root in ALLOWED_SEARCH_ROOTS):
            allowed.append(rel)
    return allowed


def read_repo_file(path: str, max_chars: int = 12000, repo_root: str | Path | None = None) -> str:
    """Read a safe, allowlisted project file."""
    rel = _relative_path(path, repo_root)
    if not _is_allowed_file(rel):
        raise ValueError(f"Archivo no permitido para lectura: {rel}")
    root = _repo_root(repo_root)
    abs_path = root / rel
    if not abs_path.is_file():
        raise FileNotFoundError(rel)
    text = abs_path.read_text(encoding="utf-8", errors="replace")
    limit = max(1000, min(int(max_chars or 12000), 50000))
    if len(text) > limit:
        return text[:limit] + "\n\n[contenido truncado por limite de lectura]"
    return text


def list_editor_files(repo_root: str | Path | None = None) -> List[str]:
    """Return the canonical files the advisor should consider for the editor."""
    root = _repo_root(repo_root)
    return sorted(rel for rel in ALLOWED_READ_FILES if (root / rel).exists())


def search_repo(
    pattern: str,
    paths: Iterable[str] | None = None,
    max_matches: int = 80,
    repo_root: str | Path | None = None,
) -> str:
    """Search safe project areas with ripgrep and return compact text output."""
    if not pattern or len(pattern.strip()) < 2:
        raise ValueError("El patron de busqueda debe tener al menos 2 caracteres.")
    root = _repo_root(repo_root)
    targets = _allowed_search_targets(paths, root)
    if not targets:
        return ""
    limit = max(1, min(int(max_matches or 80), 200))
    command = ["rg", "-n", "--no-heading", "--color", "never", "-m", str(limit), pattern, *targets]
    try:
        result = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ripgrep no esta disponible en este entorno.") from exc
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "Fallo al buscar en el repositorio.")
    lines = result.stdout.splitlines()[:limit]
    return "\n".join(lines)


def summarize_editor_architecture(repo_root: str | Path | None = None) -> str:
    """Return a compact, deterministic architecture brief for the advisor prompt."""
    files = list_editor_files(repo_root)
    service_files = [item for item in files if item.startswith("services/")]
    engine_files = [item for item in files if item.startswith("engines/")]
    return "\n".join(
        [
            "Editor Visual IA Offset - resumen base:",
            "- Frontend canonico: templates/editor_offset_visual.html, static/js/editor_offset_visual.js, static/css/editor_offset_visual.css.",
            "- Fachada Flask: routes.py. No asumir que toda la logica vive alli; parte ya fue extraida a services/.",
            "- Motor principal de imposicion: engines/step_repeat_pro_engine.py.",
            "- Selector de motores: services/editor_offset_imposition_service.py.",
            "- Salida preview/PDF: montaje_offset_inteligente.py con validacion en services/editor_offset_output_contract.py.",
            "- Simulador aislado: cuadernillos/simulator.py.",
            f"- Servicios disponibles: {', '.join(service_files) or 'ninguno detectado'}.",
            f"- Motores disponibles: {', '.join(engine_files) or 'ninguno detectado'}.",
        ]
    )


def _unique_sorted(values: Iterable[str]) -> List[str]:
    return sorted({value for value in values if value})


def summarize_editor_ux_surface(repo_root: str | Path | None = None) -> str:
    """Return deterministic UX/DOM signals for the Editor Visual IA surface."""
    html = read_repo_file("templates/editor_offset_visual.html", max_chars=50000, repo_root=repo_root)
    js = read_repo_file("static/js/editor_offset_visual.js", max_chars=50000, repo_root=repo_root)
    css = read_repo_file("static/css/editor_offset_visual.css", max_chars=50000, repo_root=repo_root)

    tabs = _unique_sorted(re.findall(r'data-editor-tab="([^"]+)"', html))
    panels = _unique_sorted(re.findall(r'data-editor-tab-panel="([^"]+)"', html))
    html_ids = _unique_sorted(re.findall(r'\sid="([^"]+)"', html))
    js_ids = _unique_sorted(re.findall(r"getElementById\('([^']+)'\)", js))
    missing_html_ids = [item for item in js_ids if item not in html_ids]
    css_selectors = [
        ".editor-header",
        ".editor-shell",
        ".editor-topbar",
        ".editor-workspace",
        ".sheet-toolbar",
        ".sheet-subtoolbar",
        ".control-block",
        ".manual-tools",
        ".sheet-wrapper",
        ".zoom-controls",
        ".sheet-canvas",
        ".side-panel",
        ".editor-tabs",
        ".editor-tab",
        ".editor-tab-panels",
        ".editor-tab-panel",
        ".panel-accordion",
        ".geometry-validation-panel",
        ".manual-advanced-tools",
        ".ai-panel",
    ]
    present_css_selectors = [selector for selector in css_selectors if selector in css]
    listener_count = len(re.findall(r"\.addEventListener\(", js))
    direct_id_lookup_count = len(js_ids)

    structure_selectors = [
        ".editor-header",
        ".editor-topbar",
        ".sheet-toolbar",
        ".sheet-subtoolbar",
        ".editor-workspace",
        ".sheet-wrapper",
        ".sheet-canvas",
        ".zoom-controls",
        ".geometry-validation-panel",
        ".side-panel",
        ".editor-tabs",
        ".editor-tab-panels",
    ]
    present_structure = [selector for selector in structure_selectors if selector in html or selector in css]
    canvas_ids = [item for item in ["sheet-canvas", "sheet", "zoom-in", "zoom-out", "zoom-label"] if item in html_ids]
    geometry_ids = [
        item
        for item in ["geometry-validation-panel", "geometry-validation-summary", "geometry-validation-list"]
        if item in html_ids
    ]
    topbar_ids = [
        item
        for item in [
            "btn-save",
            "btn-auto",
            "btn-new-slot",
            "btn-dup-slot",
            "btn-del-slot",
            "btn-group-slots",
            "btn-ungroup-slots",
            "face-front",
            "face-back",
            "btn-duplicate-face",
        ]
        if item in html_ids
    ]
    snap_spacing_ids = [
        item
        for item in [
            "snap-slots",
            "snap-margins",
            "snap-grid",
            "snap-tolerance",
            "spacing-x",
            "spacing-y",
            "btn-spacing-apply-all",
            "btn-spacing-rows",
            "btn-spacing-cols",
            "btn-spacing-live",
        ]
        if item in html_ids
    ]
    edition_ids = [
        item
        for item in html_ids
        if item.startswith(("btn-select-", "btn-center-", "btn-nudge-", "btn-align-", "btn-distribute-"))
        or item in {"nudge-step", "btn-manual-advanced-toggle", "manual-advanced-tools"}
    ]
    sensitive_listener_ids = [
        item
        for item in [
            *topbar_ids,
            *snap_spacing_ids,
            *edition_ids,
            *canvas_ids,
            "btn-preview",
            "btn-pdf",
            "btn-apply-imposition",
            "btn-ai-run",
            "btn-ai-apply",
            "btn-cuadernillo-simular",
            "btn-ctp-apply",
            "btn-ctp-disable",
        ]
        if item in js_ids
    ]

    critical_ids = [
        item
        for item in html_ids
        if item.startswith(("btn-", "editor-tab-", "slot-", "ctp-", "sheet", "geometry-", "ai-"))
    ]

    lines = [
        "Superficie UX del Editor Visual IA:",
        f"- Shell detectado: {', '.join(present_structure) or 'sin selectores principales detectados'}.",
        f"- Header/topbar/subtoolbar: header={'.editor-header' in present_css_selectors}, topbar={'.editor-topbar' in present_css_selectors}, toolbar={'.sheet-toolbar' in present_css_selectors}, subtoolbar={'.sheet-subtoolbar' in present_css_selectors}.",
        f"- Workspace principal: editor-workspace={'.editor-workspace' in present_css_selectors}, sheet-wrapper={'.sheet-wrapper' in present_css_selectors}.",
        f"- Canvas/sheet/zoom: ids {', '.join(canvas_ids) or 'ninguno detectado'}; selectores CSS canvas presentes: {', '.join(selector for selector in ['.sheet-canvas', '.zoom-controls'] if selector in present_css_selectors) or 'ninguno'}.",
        f"- Geometry panel: ids {', '.join(geometry_ids) or 'ninguno detectado'}; no duplicar geometry-validation-panel.",
        f"- Tabs del panel derecho ({len(tabs)}): {', '.join(tabs)}.",
        f"- Paneles por data-editor-tab-panel ({len(panels)}): {', '.join(panels)}.",
        f"- IDs en template: {len(html_ids)}.",
        f"- IDs buscados por JS con getElementById: {direct_id_lookup_count}.",
        f"- Listeners detectados en JS: {listener_count}.",
        f"- Selectores CSS relevantes presentes: {', '.join(present_css_selectors)}.",
        f"- IDs topbar/cara detectados: {', '.join(topbar_ids) or 'ninguno'}.",
        f"- IDs snap/spacing detectados: {', '.join(snap_spacing_ids) or 'ninguno'}.",
        f"- IDs edicion rapida detectados: {', '.join(edition_ids[:30]) or 'ninguno'}.",
        f"- IDs con listeners sensibles para Fase 10: {', '.join(sensitive_listener_ids[:50]) or 'sin muestra'}.",
        "- Zonas visuales sensibles: editor-header, editor-topbar, sheet-toolbar, sheet-subtoolbar, editor-workspace, sheet-canvas, side-panel, editor-tabs, editor-tab-panels, panel-accordion, geometry-validation-panel.",
        "- Riesgo Fase 10: compactar botones o controles puede romper legibilidad, hit area o scroll sin tocar JS; si se mueven nodos, los listeners acoplados por getElementById/querySelector deben revisarse.",
        "- Reglas SAFE: preferir CSS-only; no renombrar ids; no cambiar data-editor-tab/data-editor-tab-panel; no mover controles sin revisar listeners; no duplicar geometry-validation-panel; no tocar contratos, preview/PDF, CTP, Step & Repeat PRO ni cuadernillos.",
    ]
    if critical_ids:
        lines.append(f"- Muestra de IDs criticos: {', '.join(critical_ids[:40])}.")
    if missing_html_ids:
        lines.append(f"- IDs buscados por JS sin match HTML directo: {', '.join(missing_html_ids[:40])}.")
    else:
        lines.append("- No se detectaron IDs buscados por JS sin match HTML directo en la muestra leida.")
    return "\n".join(lines)


def list_validation_commands() -> List[str]:
    """Return safe validation commands for future implementation work."""
    return [
        "python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies",
        "git diff --check",
        "node --check static/js/editor_offset_visual.js",
        "pytest",
        "venv\\Scripts\\pytest.exe tests/playwright/test_editor_load.py -s",
    ]
