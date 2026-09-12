"""Canonical, transport-neutral contract for the first V2 preflight gate."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final


PREFLIGHT_REPORT_SCHEMA_VERSION: Final = 1
PREFLIGHT_POLICY_ID: Final = "editor-offset-v2-minimal"
PREFLIGHT_POLICY_VERSION: Final = "1"
PREFLIGHT_CAPABILITIES_ID: Final = "diagnostic-only"
PREFLIGHT_CAPABILITIES_VERSION: Final = "1"
PREFLIGHT_ANALYZER_ID: Final = "editor-offset-v2-preflight"
PREFLIGHT_ANALYZER_VERSION: Final = "1"
PREFLIGHT_OPERATIONS: Final = ("preview", "pdf_final", "ctp")
PREFLIGHT_CHECK_STATUSES: Final = frozenset(
    {"passed", "findings", "not_applicable", "not_run", "failed"}
)
PREFLIGHT_SEVERITIES: Final = frozenset({"info", "warning", "error"})


class PreflightContractError(ValueError):
    """Raised when a generated report cannot satisfy its stable contract."""


def validate_preflight_report(report: Mapping[str, object]) -> None:
    """Validate the report envelope before publishing it atomically.

    Detailed physical evidence is produced by the application service. This
    boundary catches missing envelope members, invalid enum values and malformed
    check/issue references without turning the report into a second Layout V2.
    """

    required = {
        "report_schema_version", "report_id", "scope", "subject", "inputs",
        "policy", "capabilities", "analyzer", "started_at", "completed_at",
        "execution", "checks", "issues", "decisions",
    }
    if set(report) != required:
        raise PreflightContractError("Report fields do not match the canonical envelope")
    if report["report_schema_version"] != PREFLIGHT_REPORT_SCHEMA_VERSION:
        raise PreflightContractError("Unsupported preflight report schema version")
    if report["scope"] != "layout" or not isinstance(report["report_id"], str):
        raise PreflightContractError("A layout report requires a string report_id")
    subject = report["subject"]
    if not isinstance(subject, Mapping) or not isinstance(subject.get("job_id"), str):
        raise PreflightContractError("Layout report subject must identify a job")
    if report["execution"] not in {"complete", "incomplete"}:
        raise PreflightContractError("Invalid preflight execution state")
    checks = report["checks"]
    issues = report["issues"]
    decisions = report["decisions"]
    if not isinstance(checks, list) or not isinstance(issues, list) or not isinstance(decisions, list):
        raise PreflightContractError("Checks, issues and decisions must be arrays")
    check_ids = set()
    issue_ids = set()
    for check in checks:
        if not isinstance(check, Mapping) or not isinstance(check.get("check_id"), str):
            raise PreflightContractError("Every check requires a check_id")
        if check["status"] not in PREFLIGHT_CHECK_STATUSES:
            raise PreflightContractError("Invalid preflight check status")
        check_ids.add(check["check_id"])
    for issue in issues:
        if not isinstance(issue, Mapping) or not isinstance(issue.get("issue_id"), str):
            raise PreflightContractError("Every issue requires an issue_id")
        if issue["severity"] not in PREFLIGHT_SEVERITIES:
            raise PreflightContractError("Invalid preflight issue severity")
        if issue.get("check_id") not in check_ids:
            raise PreflightContractError("Issue references an unknown check")
        if not isinstance(issue.get("blocks"), list):
            raise PreflightContractError("Issue blocks must be an array")
        issue_ids.add(issue["issue_id"])
    for check in checks:
        if any(issue_id not in issue_ids for issue_id in check.get("issue_ids", [])):
            raise PreflightContractError("Check references an unknown issue")
    for decision in decisions:
        if not isinstance(decision, Mapping) or decision.get("operation") not in PREFLIGHT_OPERATIONS:
            raise PreflightContractError("Invalid preflight decision operation")
        if decision.get("status") not in {"eligible", "blocked"}:
            raise PreflightContractError("Invalid preflight decision status")
        if any(issue_id not in issue_ids for issue_id in decision.get("blocking_issue_ids", [])):
            raise PreflightContractError("Decision references an unknown issue")


__all__ = [
    "PREFLIGHT_ANALYZER_ID",
    "PREFLIGHT_ANALYZER_VERSION",
    "PREFLIGHT_CAPABILITIES_ID",
    "PREFLIGHT_CAPABILITIES_VERSION",
    "PREFLIGHT_CHECK_STATUSES",
    "PREFLIGHT_OPERATIONS",
    "PREFLIGHT_POLICY_ID",
    "PREFLIGHT_POLICY_VERSION",
    "PREFLIGHT_REPORT_SCHEMA_VERSION",
    "PREFLIGHT_SEVERITIES",
    "PreflightContractError",
    "validate_preflight_report",
]
