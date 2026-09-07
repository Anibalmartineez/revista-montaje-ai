"""Offline characterization of the temporary V1 renderer, never a production API.

Reads a saved V2 job, renders immutable copies in an exclusive trial directory,
and records evidence. No Flask routes, V1 layouts, source edits or eligibility
decisions. Positive bleed is only allowed as an explicitly requested experiment.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz

from editor_offset_v2.infrastructure.editor_output_adapter import (
    adapt_layout_v2_to_output,
    serialize_output_job,
)
from editor_offset_v2.infrastructure.pdf_inspector import inspect_pdf


class ProbeRejected(ValueError):
    """The trial cannot run; no completed artifact directory is published."""

    def __init__(self, code: str, message: str, issues=()):
        super().__init__(message)
        self.code = code
        self.issues = tuple(issues)


@dataclass(frozen=True)
class ProbeArtifacts:
    pdf: Path
    previews: tuple[Path, ...]
    report: Path


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_physical_metadata(asset: dict, source: Path) -> None:
    inspection = inspect_pdf(source)
    if inspection.page_count != asset["page_count"]:
        raise ProbeRejected("PHYSICAL_METADATA_MISMATCH", "PDF page count changed")
    declared = {page["number"]: page for page in asset["pages"]}
    for page in inspection.pages:
        stored = declared.get(page.number)
        if stored is None or stored["intrinsic_rotation_deg"] != page.intrinsic_rotation_deg:
            raise ProbeRejected("PHYSICAL_METADATA_MISMATCH", "PDF orientation changed")
        for name, actual in page.boxes_as_layout().items():
            expected = stored["boxes_mm"][name]
            if (actual is None) != (expected is None) or (
                actual is not None
                and any(abs(actual[key] - expected[key]) > 0.01 for key in actual)
            ):
                raise ProbeRejected("PHYSICAL_METADATA_MISMATCH", f"PDF {name} box changed")
    # This experiment does not establish semantics for non-default UserUnit.
    with fitz.open(source) as document:
        for page in document:
            kind, value = document.xref_get_key(page.xref, "UserUnit")
            if kind != "null" and float(value) != 1:
                raise ProbeRejected("UNSUPPORTED_USER_UNIT", "UserUnit requires its own fixture")


def _render_face(designs: list, config):
    # Lazy import: importing the V2 application never imports the shared engine.
    from montaje_offset_inteligente import realizar_montaje_inteligente

    return realizar_montaje_inteligente(designs, config)


def _run_output_probe(
    job_root: Path,
    output_directory: Path,
    *,
    expected_revision: int,
    observe_legacy_bleed: bool = False,
    prepared_sources: bool = False,
) -> ProbeArtifacts:
    """Run a restricted offline trial against a saved Layout V2 revision.

    The caller must supply a new output directory outside the source job. The
    existing adapter's capability restrictions remain intact. This function is
    a characterization harness, not the preflight contract specified in doc 21.
    ``observe_legacy_bleed`` records synthetic bleed behavior, without claiming
    equivalence to V2's original bleed or clipping policy.
    """
    root = Path(job_root).resolve(strict=True)
    destination = Path(output_directory).resolve()
    if destination == root or destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ProbeRejected("UNSAFE_OUTPUT_DIRECTORY", "Trial output must be outside the source job")
    if destination.exists():
        raise ProbeRejected("OUTPUT_ALREADY_EXISTS", "Trial artifacts cannot be overwritten")
    layout_path = root / "layout_v2.json"
    if not layout_path.resolve().is_relative_to(root):
        raise ProbeRejected("UNSAFE_LAYOUT_PATH", "Layout must remain inside the source job")
    layout_bytes = layout_path.read_bytes()
    layout = json.loads(layout_bytes)
    if layout.get("job", {}).get("revision") != expected_revision:
        raise ProbeRejected("STALE_REVISION", "Saved revision differs from the requested trial")
    if prepared_sources:
        from .prepared_output_adapter import adapt_prepared_trial
        result = adapt_prepared_trial(layout, root)
    else:
        result = adapt_layout_v2_to_output(layout, root)
    if not result.success:
        raise ProbeRejected("ADAPTER_REJECTED", "Layout is outside the current bridge capabilities", result.issues)
    job = result.job
    assert job is not None
    if layout["faces"]["duplex"]["enabled"]:
        raise ProbeRejected("DUPLEX_NOT_CHARACTERIZED", "Two explicit faces are supported; duplex flipping is not")
    if len(layout["slots"]) > 200 or job.sheet_size.width > 1000 or job.sheet_size.height > 1400:
        raise ProbeRejected("TRIAL_RESOURCE_LIMIT", "Trial exceeds the offline fixture limits")
    positive_bleed = any(slot["geometry"]["bleed_mm"] > 0 for slot in layout["slots"])
    if positive_bleed and not observe_legacy_bleed and not prepared_sources:
        raise ProbeRejected("BLEED_POLICY_UNRESOLVED", "Explicit observation is required for legacy mirror bleed")

    # Capture bytes before calling the shared renderer; it never sees originals.
    assets = {asset["id"]: asset for asset in layout["assets"]}
    captured = {}
    original_paths = {}
    for design in job.designs:
        if design.asset_id in captured:
            continue
        if design.source_path.stat().st_size > 50 * 1024 * 1024:
            raise ProbeRejected("TRIAL_RESOURCE_LIMIT", "Asset exceeds 50 MiB")
        data = design.source_path.read_bytes()
        if _digest(data) != assets[design.asset_id]["sha256"]:
            raise ProbeRejected("ASSET_HASH_MISMATCH", "Physical source differs from saved asset identity")
        captured[design.asset_id] = data
        original_paths[design.asset_id] = design.source_path

    destination.parent.mkdir(parents=True, exist_ok=True)
    # TemporaryDirectory owns only this fresh sibling directory. On any failure
    # it removes trial files, never the source job or an existing destination.
    with TemporaryDirectory(prefix=".v2-output-probe-", dir=destination.parent) as temporary:
        stage = Path(temporary).resolve()
        source_dir = stage / "sources"
        source_dir.mkdir()
        snapshot_paths = {}
        for index, (asset_id, data) in enumerate(captured.items()):
            snapshot = source_dir / f"asset_{index}.pdf"
            snapshot.write_bytes(data)
            _check_physical_metadata(assets[asset_id], snapshot)
            snapshot_paths[asset_id] = snapshot
        staged_job = replace(job, designs=tuple(
            replace(design, source_path=snapshot_paths[design.asset_id])
            for design in job.designs
        ))
        payload = serialize_output_job(staged_job)
        from montaje_offset_inteligente import Diseno, MontajeConfig
        from montaje_offset import generar_vista_previa

        designs = [Diseno(ruta=str(design.source_path), cantidad=1) for design in staged_job.designs]
        preparation_evidence = []
        if prepared_sources:
            from .prepared_output_adapter import prepare_renderer_inputs, overlay_slot_crop_marks
            paths, payload, preparation_evidence = prepare_renderer_inputs(
                staged_job, layout, snapshot_paths, stage,
                allow_mirror_bleed=observe_legacy_bleed,
            )
            designs = [Diseno(ruta=str(path), cantidad=1) for path in paths]
        face_pdfs = []
        preview_names = []
        applied_positions = {}
        for face in job.export.face_order:
            positions = payload["faces"][face]["posiciones_manual"]
            # V2 uses counter-clockwise rotation. V1's raster path negates it;
            # its vector overlay receives the positive angle directly.
            if job.export.render_mode == "raster":
                positions = [dict(pos, rot_deg=(-pos["rot_deg"]) % 360) for pos in positions]
            face_pdf = stage / f"{face}.pdf"
            config = MontajeConfig(
                tamano_pliego=(job.sheet_size.width, job.sheet_size.height),
                margen_izquierdo=job.margins.left, margen_derecho=job.margins.right,
                margen_superior=job.margins.top, margen_inferior=job.margins.bottom,
                sangrado=0, separacion=0, pinza_mm=0, centrar=False,
                permitir_rotacion=False, ordenar_tamano=False, usar_trimbox=True,
                modo_manual=True, estrategia="manual", posiciones_manual=positions,
                output_mode=job.export.render_mode, output_path=str(face_pdf),
                preview_path=None, es_pdf_final=True, devolver_posiciones=True,
                cutmarks_por_forma=False if prepared_sources else payload["faces"][face]["cutmarks_por_forma"],
                ctp_config={"enabled": False}, export_area_util=False,
            )
            rendered = _render_face(designs, config)
            if prepared_sources:
                overlay_slot_crop_marks(face_pdf, job, face)
            applied_positions[face] = [
                {key: value for key, value in pos.items() if key not in {"archivo", "ruta_pdf"}}
                for pos in rendered["positions"]
            ]
            with fitz.open(face_pdf) as document:
                if document.page_count != 1:
                    raise ProbeRejected("INVALID_RENDERED_PAGES", "Each face must produce one PDF page")
                rect = document[0].rect
                if any(abs(actual * 25.4 / 72 - expected) > 0.01 for actual, expected in (
                    (rect.width, job.sheet_size.width), (rect.height, job.sheet_size.height),
                )):
                    raise ProbeRejected("INVALID_RENDERED_SHEET", "Renderer changed the sheet dimensions")
            preview_name = f"{face}.png"
            generar_vista_previa(str(face_pdf), str(stage / preview_name))
            preview_names.append(preview_name)
            face_pdfs.append(face_pdf)

        # Same front/back concatenation used by the V1 output service.
        from PyPDF2 import PdfReader, PdfWriter

        writer = PdfWriter()
        for face_pdf in face_pdfs:
            reader = PdfReader(str(face_pdf))
            for page in reader.pages:
                writer.add_page(page)
        with (stage / "trial.pdf").open("xb") as stream:
            writer.write(stream)
        if layout_path.read_bytes() != layout_bytes or any(
            _digest(path.read_bytes()) != _digest(captured[asset_id])
            for asset_id, path in original_paths.items()
        ):
            raise ProbeRejected("INPUT_CHANGED_DURING_TRIAL", "Source job changed during rendering")
        notes = ["Experimental artifact: no production preflight or canvas parity certification.",
                 "Legacy per-slot crop-mark selection and zero-bleed marks are not faithful."]
        if positive_bleed and not prepared_sources:
            notes.append("Requested observation: V1 replaces original bleed with mirrored trim edges.")
            if job.export.render_mode == "vector_hybrid":
                notes.append("Raster bleed frame and vector center use different rotation paths; parity is unproven.")
        if prepared_sources:
            notes = ["Experimental prepared-source artifact; production preflight remains pending.",
                     "PDF boxes and pages are normalized before V1 placement; sources are unchanged.",
                     "Crop marks follow each slot; zero-bleed ticks have an explicit trial length of 3 mm."]
        report = {
            "probe_version": 1, "production_ready": False,
            "job_id": job.id, "revision": expected_revision,
            "layout_sha256": _digest(layout_bytes), "render_mode": job.export.render_mode,
            "sheet_mm": payload["sheet_mm"],
            "source_selections": [{"asset_id": design.asset_id, "page": design.page,
                                   "pdf_box": design.pdf_box,
                                   "intrinsic_rotation_deg": design.intrinsic_rotation_deg}
                                  for design in job.designs],
            "runtime": {"pymupdf": fitz.VersionBind},
            "sources": [{"asset_id": key, "sha256": _digest(value),
                         "snapshot": str(snapshot_paths[key].relative_to(stage))}
                        for key, value in captured.items()],
            "face_order": list(job.export.face_order), "positions": applied_positions,
            "issues": [issue.as_dict() for issue in result.issues], "notes": notes,
            "pdf": "trial.pdf", "previews": preview_names,
        }
        if prepared_sources:
            report.update(preparation=preparation_evidence, allow_mirror_bleed=observe_legacy_bleed)
        (stage / "layout_v2.snapshot.json").write_bytes(layout_bytes)
        (stage / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Recheck at publication; rename refuses to replace existing directories.
        if destination.exists():
            raise ProbeRejected("OUTPUT_ALREADY_EXISTS", "Trial destination appeared during rendering")
        stage.rename(destination)
    return ProbeArtifacts(destination / "trial.pdf", tuple(destination / name for name in preview_names), destination / "report.json")


def run_legacy_output_probe(job_root, output_directory, *, expected_revision, observe_legacy_bleed=False):
    """Original phase-22 characterization, with its strict legacy limitations."""
    return _run_output_probe(job_root, output_directory, expected_revision=expected_revision,
                             observe_legacy_bleed=observe_legacy_bleed)


def run_prepared_output_probe(job_root, output_directory, *, expected_revision, allow_mirror_bleed=False):
    """Phase-23 trial using V2 page/box preparation and per-slot marks."""
    return _run_output_probe(job_root, output_directory, expected_revision=expected_revision,
                             observe_legacy_bleed=allow_mirror_bleed, prepared_sources=True)
