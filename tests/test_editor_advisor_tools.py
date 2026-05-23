import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ai_agent.editor_advisor import tools
from ai_agent.editor_advisor.schemas import EditorAdvisorReport


def test_list_editor_files_includes_canonical_editor_files():
    files = tools.list_editor_files()

    assert "AGENTS.md" in files
    assert "templates/editor_offset_visual.html" in files
    assert "static/js/editor_offset_visual.js" in files
    assert "services/editor_offset_imposition_service.py" in files


def test_read_repo_file_allows_only_allowlisted_files():
    content = tools.read_repo_file("AGENTS.md", max_chars=2000)

    assert "AM GROUP AI BUILDER" in content
    with pytest.raises(ValueError):
        tools.read_repo_file(".env")
    with pytest.raises(ValueError):
        tools.read_repo_file("static/js/../uploads/example.pdf")


def test_read_repo_file_blocks_paths_outside_repo():
    outside = tools.REPO_ROOT.parent / "outside-revista-montaje-ai.txt"
    with pytest.raises(ValueError):
        tools.read_repo_file(str(outside))


def test_search_repo_uses_safe_roots_only():
    output = tools.search_repo("Step Repeat", paths=["DOCS/OFFSET"], max_matches=5)

    assert "DOCS/OFFSET" in output or output == ""
    with pytest.raises(ValueError):
        tools.search_repo("SECRET", paths=[".env"], max_matches=5)


def test_validation_commands_are_read_only_recommendations():
    commands = tools.list_validation_commands()

    assert any("compileall" in command for command in commands)
    assert all("rm " not in command.lower() for command in commands)


def test_ux_surface_summary_reports_right_panel_signals():
    summary = tools.summarize_editor_ux_surface()

    assert "Superficie UX del Editor Visual IA" in summary
    assert "Tabs del panel derecho" in summary
    assert "editor-tab-panels" in summary
    assert "geometry-validation-panel" in summary
    assert "getElementById" in summary
    assert "no renombrar ids" in summary


def test_editor_advisor_report_keeps_legacy_fields_and_ux_defaults():
    report = EditorAdvisorReport()

    assert report.fortalezas_actuales == []
    assert report.problemas_detectados == []
    assert report.problemas_ux_visuales == []
    assert report.riesgos_dom_listeners == []
    assert report.cambios_css_only_seguros == []
    assert report.cambios_html_js_riesgosos == []
    assert report.zonas_peligrosas_de_tocar == []
    assert report.checklist_ux_antes == []
    assert report.checklist_ux_despues == []
    assert report.fase_safe_sugerida == ""
