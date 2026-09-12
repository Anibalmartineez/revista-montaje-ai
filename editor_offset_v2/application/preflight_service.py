"""Read-only physical and geometric preflight for a saved Layout V2 snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from editor_offset_v2.domain.geometry import (
    Bounds,
    Point,
    Size,
    SlotGeometry,
    bleed_polygon,
    polygon_within_bounds,
    polygons_intersect,
    sheet_bounds,
    trim_polygon,
)
from editor_offset_v2.domain.preflight_contract import (
    PREFLIGHT_ANALYZER_ID,
    PREFLIGHT_ANALYZER_VERSION,
    PREFLIGHT_CAPABILITIES_ID,
    PREFLIGHT_CAPABILITIES_VERSION,
    PREFLIGHT_OPERATIONS,
    PREFLIGHT_POLICY_ID,
    PREFLIGHT_POLICY_VERSION,
    PREFLIGHT_REPORT_SCHEMA_VERSION,
    PreflightContractError,
    validate_preflight_report,
)
from editor_offset_v2.domain.validation import validate_layout_v2
from editor_offset_v2.infrastructure.asset_repository import (
    AssetRepository,
    AssetRepositoryError,
    SOURCE_FILENAME,
)
from editor_offset_v2.infrastructure.pdf_inspector import PdfInspectionError, inspect_pdf
from editor_offset_v2.infrastructure.job_repository import JobRepository, JobRepositoryError


PDF_METADATA_TOLERANCE_MM = 0.01


class PreflightServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.issues: tuple[object, ...] = ()
        super().__init__(message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _same_number(left: object, right: object) -> bool:
    return abs(float(left) - float(right)) <= PDF_METADATA_TOLERANCE_MM


def _issue(
    *,
    issue_id: str,
    check_id: str,
    code: str,
    severity: str,
    message: str,
    path: str | None = None,
    asset_ids: list[str] | None = None,
    page_numbers: list[int] | None = None,
    work_ids: list[str] | None = None,
    slot_ids: list[str] | None = None,
    faces: list[str] | None = None,
    observed: object | None = None,
    expected: object | None = None,
    blocks: list[str] | None = None,
) -> dict[str, object]:
    evidence: dict[str, object] = {}
    if observed is not None:
        evidence["observed"] = observed
    if expected is not None:
        evidence["expected"] = expected
    evidence["tolerance_mm"] = PDF_METADATA_TOLERANCE_MM
    return {
        "issue_id": issue_id,
        "check_id": check_id,
        "code": code,
        "severity": severity,
        "message": message,
        "references": {
            "path": path,
            "asset_ids": asset_ids or [],
            "page_numbers": page_numbers or [],
            "work_ids": work_ids or [],
            "slot_ids": slot_ids or [],
            "faces": faces or [],
        },
        "evidence": evidence,
        "blocks": blocks or [],
    }


class PreflightService:
    def __init__(self, jobs: JobRepository):
        self._jobs = jobs
        self._assets = AssetRepository(jobs)

    def run(
        self,
        job_id: str,
        *,
        enabled_operations: Mapping[str, bool] | None = None,
    ) -> dict[str, object]:
        try:
            layout = self._jobs.read_layout(job_id)
            layout_path = self._jobs.layout_path(job_id)
            layout_bytes = layout_path.read_bytes()
        except JobRepositoryError as exc:
            status = 404 if exc.code == "JOB_NOT_FOUND" else 400 if exc.code == "INVALID_JOB_ID" else 500
            raise PreflightServiceError(exc.code, exc.message, status) from exc
        except (OSError, AssetRepositoryError) as exc:
            raise PreflightServiceError("PREFLIGHT_INPUT_UNAVAILABLE", "The saved V2 layout is unavailable") from exc
        started = _now()
        layout_hash = hashlib.sha256(layout_bytes).hexdigest()
        checks: list[dict[str, object]] = []
        issues: list[dict[str, object]] = []

        contract_issues = validate_layout_v2(layout)
        self._finish_check(
            checks, issues, "layout_contract", "Layout V2 contract", "layout", contract_issues,
            lambda issue: _issue(
                issue_id=self._next_issue("layout"), check_id="layout_contract",
                code="LAYOUT_INVALID", severity="error", message=issue.message,
                path=issue.path, blocks=list(PREFLIGHT_OPERATIONS),
            ),
        )
        used_assets = {slot["source"]["asset_id"] for slot in layout["slots"]}
        asset_slots: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for slot in layout["slots"]:
            asset_slots[slot["source"]["asset_id"]].append(slot)
        physical_issues: list[dict[str, object]] = []
        physical_evidence: list[dict[str, object]] = []
        assets = {asset["id"]: asset for asset in layout["assets"]}
        for asset_id in sorted(used_assets):
            asset = assets.get(asset_id)
            check_id = "asset_identity"
            if asset is None:
                physical_issues.append(_issue(
                    issue_id=self._next_issue("missing-asset"), check_id=check_id,
                    code="ASSET_MISSING", severity="error", message="The used asset is missing from Layout V2.",
                    path="$.assets", asset_ids=[asset_id], blocks=list(PREFLIGHT_OPERATIONS),
                ))
                continue
            try:
                asset_dir = self._assets.asset_path(job_id, asset_id)
                source = asset_dir / SOURCE_FILENAME
                if asset_dir.is_symlink() or source.is_symlink() or not source.resolve().is_relative_to(asset_dir.resolve()):
                    raise AssetRepositoryError("ASSET_UNSAFE_PATH", "The asset source path is unsafe")
                data = source.read_bytes()
            except (AssetRepositoryError, OSError, ValueError) as exc:
                physical_issues.append(_issue(
                    issue_id=self._next_issue("asset-path"), check_id=check_id,
                    code="ASSET_UNSAFE_PATH" if isinstance(exc, AssetRepositoryError) else "ASSET_MISSING",
                    severity="error", message=str(exc), path=f"$.assets[{asset_id}].storage_key",
                    asset_ids=[asset_id], blocks=list(PREFLIGHT_OPERATIONS),
                ))
                continue
            digest = hashlib.sha256(data).hexdigest()
            if digest != asset["sha256"]:
                physical_issues.append(_issue(
                    issue_id=self._next_issue("asset-hash"), check_id=check_id,
                    code="ASSET_IDENTITY_MISMATCH", severity="error",
                    message="The physical PDF hash differs from the saved asset identity.",
                    path=f"$.assets[{asset_id}].sha256", asset_ids=[asset_id],
                    observed=digest, expected=asset["sha256"], blocks=list(PREFLIGHT_OPERATIONS),
                ))
                continue
            try:
                inspection = inspect_pdf(data)
            except PdfInspectionError as exc:
                physical_issues.append(_issue(
                    issue_id=self._next_issue("pdf-unreadable"), check_id=check_id,
                    code="PDF_UNREADABLE", severity="error", message=str(exc),
                    path=f"$.assets[{asset_id}].storage_key", asset_ids=[asset_id],
                    blocks=list(PREFLIGHT_OPERATIONS),
                ))
                continue
            physical_evidence.append({"asset_id": asset_id, "sha256": digest, "page_count": inspection.page_count})
            declared_pages = {page["number"]: page for page in asset["pages"]}
            if asset["page_count"] != inspection.page_count:
                physical_issues.append(_issue(
                    issue_id=self._next_issue("pdf-page-count"), check_id=check_id,
                    code="PDF_METADATA_MISMATCH", severity="error",
                    message="PDF page count differs from the saved physical metadata.",
                    path=f"$.assets[{asset_id}].page_count", asset_ids=[asset_id],
                    observed=inspection.page_count, expected=asset["page_count"],
                    blocks=list(PREFLIGHT_OPERATIONS),
                ))
            for page in inspection.pages:
                declared = declared_pages.get(page.number)
                if declared is None or declared["intrinsic_rotation_deg"] != page.intrinsic_rotation_deg:
                    physical_issues.append(_issue(
                        issue_id=self._next_issue("pdf-metadata"), check_id=check_id,
                        code="PDF_METADATA_MISMATCH", severity="error",
                        message="PDF page count or intrinsic rotation differs from Layout V2 metadata.",
                        path=f"$.assets[{asset_id}].pages", asset_ids=[asset_id], page_numbers=[page.number],
                        observed={"rotation": page.intrinsic_rotation_deg},
                        expected={"rotation": declared["intrinsic_rotation_deg"] if declared else None},
                        blocks=list(PREFLIGHT_OPERATIONS),
                    ))
                    continue
                for box_name, actual in page.boxes_as_layout().items():
                    expected = declared["boxes_mm"].get(box_name)
                    if (actual is None) != (expected is None) or (
                        actual is not None and expected is not None and any(
                            not _same_number(actual[key], expected[key]) for key in actual
                        )
                    ):
                        physical_issues.append(_issue(
                            issue_id=self._next_issue("pdf-box"), check_id=check_id,
                            code="PDF_METADATA_MISMATCH", severity="error",
                            message=f"PDF {box_name} differs from the saved physical metadata.",
                            path=f"$.assets[{asset_id}].pages[{page.number}].boxes_mm.{box_name}",
                            asset_ids=[asset_id], page_numbers=[page.number], observed=actual, expected=expected,
                            blocks=list(PREFLIGHT_OPERATIONS),
                        ))
            for slot in asset_slots[asset_id]:
                page = declared_pages.get(slot["source"]["page"])
                selected = page and page["boxes_mm"].get(slot["source"]["pdf_box"])
                if selected is None:
                    physical_issues.append(_issue(
                        issue_id=self._next_issue("selected-box"), check_id=check_id,
                        code="PDF_SEMANTICS_UNSUPPORTED", severity="error",
                        message="The selected page or PDF box is absent from the physical source.",
                        path="$.slots[].source", asset_ids=[asset_id], page_numbers=[slot["source"]["page"]],
                        slot_ids=[slot["id"]], faces=[slot["face"]], blocks=list(PREFLIGHT_OPERATIONS),
                    ))
        self._append_check(checks, "asset_identity", "Asset identity and physical source", physical_issues, physical_evidence)
        issues.extend(physical_issues)

        geometry_issues, geometry_evidence = self._geometry_findings(layout)
        self._append_check(checks, "geometry", "Trim, bleed and face geometry", geometry_issues, geometry_evidence)
        issues.extend(geometry_issues)

        capability_issues = []
        from editor_offset_v2.application.output_service import validate_output_capabilities
        for original in validate_output_capabilities(layout):
            if original.code in {"ASSET_PREFLIGHT_WARNING"}:
                continue
            mapped = "OUTPUT_FEATURE_UNSUPPORTED" if original.code.startswith("UNSUPPORTED_") else original.code
            capability_issues.append(_issue(
                issue_id=self._next_issue("capability"), check_id="capabilities",
                code=mapped, severity="error" if original.level == "error" else "warning",
                message=original.message, path=original.path, asset_ids=[original.asset_id] if original.asset_id else [],
                slot_ids=[original.slot_id] if original.slot_id else [], blocks=["pdf_final", "ctp"],
            ))
        self._append_check(checks, "capabilities", "Current output capabilities", capability_issues, {"source": "output-capabilities"})
        issues.extend(capability_issues)

        complete = all(check["status"] != "failed" and check["status"] != "not_run" for check in checks)
        enabled = {
            operation: bool((enabled_operations or {}).get(operation, False))
            for operation in PREFLIGHT_OPERATIONS
        }
        decisions = []
        for operation in PREFLIGHT_OPERATIONS:
            blocking = [
                issue["issue_id"]
                for issue in issues
                if issue["severity"] == "error" and operation in issue.get("blocks", [])
            ]
            if complete is False:
                status = "blocked"
                reason_codes = ["PREFLIGHT_INCOMPLETE"]
            elif blocking:
                status = "blocked"
                reason_codes = ["PREFLIGHT_FINDINGS"]
            elif not enabled[operation]:
                status = "blocked"
                reason_codes = ["CAPABILITY_GATE_NOT_ENABLED"]
            else:
                status = "eligible"
                reason_codes = []
            decisions.append({
                "operation": operation,
                "status": status,
                "blocking_issue_ids": blocking,
                "reason_codes": reason_codes,
            })
        report = {
            "report_schema_version": PREFLIGHT_REPORT_SCHEMA_VERSION,
            "report_id": f"pfr_{secrets.token_hex(12)}",
            "scope": "layout",
            "subject": {"job_id": job_id, "revision": layout["job"]["revision"], "layout_sha256": layout_hash},
            "inputs": {"assets": physical_evidence, "faces": list(layout["faces"]["enabled"]), "operations": list(PREFLIGHT_OPERATIONS)},
            "policy": {"id": PREFLIGHT_POLICY_ID, "version": PREFLIGHT_POLICY_VERSION, "tolerances": {"pdf_metadata_mm": PDF_METADATA_TOLERANCE_MM}},
            "capabilities": {
                "id": PREFLIGHT_CAPABILITIES_ID,
                "version": PREFLIGHT_CAPABILITIES_VERSION,
                "enabled": [operation for operation, active in enabled.items() if active],
            },
            "analyzer": {"id": PREFLIGHT_ANALYZER_ID, "version": PREFLIGHT_ANALYZER_VERSION, "pymupdf": self._pymupdf_version()},
            "started_at": started,
            "completed_at": _now(),
            "execution": "complete" if complete else "incomplete",
            "checks": checks,
            "issues": issues,
            "decisions": decisions,
        }
        try:
            validate_preflight_report(report)
            report_path = self._publish_report(job_id, report)
        except (PreflightContractError, OSError, TypeError, ValueError) as exc:
            raise PreflightServiceError("PREFLIGHT_PUBLISH_FAILED", "The preflight report could not be published") from exc
        report["report_path"] = report_path
        return report

    def consume(
        self,
        job_id: str,
        report: Mapping[str, object],
        operation: str,
    ) -> Mapping[str, object]:
        """Verify that a report still describes the exact saved layout."""
        if operation not in PREFLIGHT_OPERATIONS:
            raise PreflightServiceError("INVALID_PREFLIGHT_OPERATION", "The requested operation is not supported", 400)
        try:
            layout_path = self._jobs.layout_path(job_id)
            current_layout = self._jobs.read_layout(job_id)
            current_bytes = layout_path.read_bytes()
        except JobRepositoryError as exc:
            status = 404 if exc.code == "JOB_NOT_FOUND" else 400 if exc.code == "INVALID_JOB_ID" else 500
            raise PreflightServiceError(exc.code, exc.message, status) from exc
        except OSError as exc:
            raise PreflightServiceError("PREFLIGHT_INPUT_UNAVAILABLE", "The saved V2 layout is unavailable") from exc
        try:
            subject = report["subject"]
            expected_revision = subject["revision"]
            expected_hash = subject["layout_sha256"]
        except (KeyError, TypeError):
            raise PreflightServiceError("PREFLIGHT_INVALID_REPORT", "The preflight report subject is invalid", 422)
        actual_hash = hashlib.sha256(current_bytes).hexdigest()
        if expected_revision != current_layout["job"]["revision"] or expected_hash != actual_hash:
            raise PreflightServiceError(
                "PREFLIGHT_STALE",
                "The preflight report no longer matches the saved Layout V2 revision",
                409,
            )
        decision = next((item for item in report.get("decisions", []) if item.get("operation") == operation), None)
        if not isinstance(decision, Mapping):
            raise PreflightServiceError("PREFLIGHT_INVALID_REPORT", "The preflight report has no operation decision", 422)
        if decision.get("status") != "eligible":
            blocking_ids = set(decision.get("blocking_issue_ids", []))
            error = PreflightServiceError(
                "PREFLIGHT_BLOCKED",
                f"Preflight blocks {operation} for the saved Layout V2",
                422,
            )
            error.issues = tuple(
                issue for issue in report.get("issues", [])
                if isinstance(issue, Mapping) and issue.get("issue_id") in blocking_ids
            )
            if not error.issues:
                error.issues = tuple({"code": code} for code in decision.get("reason_codes", []))
            raise error
        return report

    def _geometry_findings(self, layout: dict[str, Any]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        issues: list[dict[str, object]] = []
        evidence: list[dict[str, object]] = []
        size = layout["sheet"]["size_mm"]
        margins = layout["sheet"]["printable_margins_mm"]
        sheet = Bounds(0.0, size["width"], 0.0, size["height"])
        printable = Bounds(margins["left"], size["width"] - margins["right"], margins["bottom"], size["height"] - margins["top"])
        if printable.width <= 0 or printable.height <= 0:
            issues.append(_issue(issue_id=self._next_issue("printable"), check_id="geometry", code="PRINTABLE_AREA_EMPTY", severity="error", message="Printable margins leave no usable area.", path="$.sheet.printable_margins_mm", blocks=list(PREFLIGHT_OPERATIONS)))
        face_polygons: dict[str, list[tuple[dict[str, Any], Any, Any]]] = defaultdict(list)
        for slot in layout["slots"]:
            geometry = slot["geometry"]
            slot_geometry = SlotGeometry(
                Point(geometry["position_mm"]["x_mm"], geometry["position_mm"]["y_mm"]),
                Size(geometry["trim_size_mm"]["width"], geometry["trim_size_mm"]["height"]),
                geometry["bleed_mm"], geometry["rotation_deg"],
            )
            trim = trim_polygon(slot_geometry)
            bleed = bleed_polygon(slot_geometry)
            face_polygons[slot["face"]].append((slot, trim, bleed))
            if not polygon_within_bounds(trim, sheet):
                issues.append(_issue(issue_id=self._next_issue("trim-sheet"), check_id="geometry", code="TRIM_OUTSIDE_SHEET", severity="error", message="Trim extends outside the sheet.", path=f"$.slots[{layout['slots'].index(slot)}].geometry", slot_ids=[slot["id"]], work_ids=[slot["work_id"]], faces=[slot["face"]], blocks=list(PREFLIGHT_OPERATIONS)))
            if not polygon_within_bounds(bleed, printable):
                issues.append(_issue(issue_id=self._next_issue("bleed-printable"), check_id="geometry", code="BLEED_OUTSIDE_PRINTABLE", severity="warning", message="Bleed extends outside the printable area.", path=f"$.slots[{layout['slots'].index(slot)}].geometry", slot_ids=[slot["id"]], work_ids=[slot["work_id"]], faces=[slot["face"]], blocks=["pdf_final", "ctp"]))
        for face, entries in face_polygons.items():
            for index, (left, left_trim, left_bleed) in enumerate(entries):
                for right, right_trim, right_bleed in entries[index + 1:]:
                    if polygons_intersect(left_trim, right_trim):
                        issues.append(_issue(issue_id=self._next_issue("trim-overlap"), check_id="geometry", code="TRIM_OVERLAP", severity="error", message="Trim areas overlap on the same face.", path="$.slots", slot_ids=[left["id"], right["id"]], work_ids=sorted({left["work_id"], right["work_id"]}), faces=[face], blocks=["pdf_final", "ctp"]))
                    elif polygons_intersect(left_bleed, right_bleed):
                        issues.append(_issue(issue_id=self._next_issue("bleed-overlap"), check_id="geometry", code="BLEED_OVERLAP", severity="warning", message="Bleed areas overlap on the same face.", path="$.slots", slot_ids=[left["id"], right["id"]], work_ids=sorted({left["work_id"], right["work_id"]}), faces=[face], blocks=["pdf_final", "ctp"]))
        evidence.append({"sheet_mm": [sheet.width, sheet.height], "printable_mm": {"left": printable.left, "right": printable.right, "bottom": printable.bottom, "top": printable.top}})
        return issues, evidence

    @staticmethod
    def _append_check(checks, check_id, label, issues, evidence):
        checks.append({"check_id": check_id, "scope": label, "status": "findings" if issues else "passed", "issue_ids": [issue["issue_id"] for issue in issues], "evidence": evidence})
        # The caller owns the shared report issue list; this is filled by the service wrapper.

    def _finish_check(self, checks, issues, check_id, label, scope, raw_issues, converter):
        converted = [converter(issue) for issue in raw_issues]
        checks.append({"check_id": check_id, "scope": scope, "status": "findings" if converted else "passed", "issue_ids": [issue["issue_id"] for issue in converted], "evidence": {"label": label}})
        issues.extend(converted)

    @staticmethod
    def _next_issue(prefix: str) -> str:
        # Prefixes are stable for humans; a per-report counter is unnecessary for
        # the first gate because each call has one service-local sequence.
        return f"{prefix}_{secrets.token_hex(6)}"

    @staticmethod
    def _pymupdf_version() -> str:
        try:
            import fitz
            return getattr(fitz, "__doc__", "PyMuPDF").split()[1]
        except Exception:
            return "unknown"

    def _publish_report(self, job_id: str, report: dict[str, object]) -> str:
        reports = self._jobs.job_path(job_id) / "reports"
        reports.mkdir(exist_ok=True)
        relative = f"reports/{report['report_id']}.json"
        target = reports / f"{report['report_id']}.json"
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=reports, delete=False, prefix=".preflight-", suffix=".tmp") as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.replace(temporary, target)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        return relative


__all__ = ["PDF_METADATA_TOLERANCE_MM", "PreflightService", "PreflightServiceError"]
