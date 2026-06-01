import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ai_agent.editor_advisor import tools
from ai_agent.editor_advisor.cli import _format_report_output
from ai_agent.editor_advisor.schemas import EditorAdvisorReport


def test_list_editor_files_includes_canonical_editor_files():
    files = tools.list_editor_files()

    assert "AGENTS.md" in files
    assert "templates/editor_offset_visual.html" in files
    assert "static/js/editor_offset_visual.js" in files
    assert "static/js/editor_offset_visual/api_client.js" in files
    assert "static/js/editor_offset_visual/booklet_panel.js" in files
    assert "services/editor_offset_http_service.py" in files
    assert "services/editor_offset_imposition_service.py" in files
    assert "services/editor_offset_output_service.py" in files
    assert "ai_agent/tools_repeat.py" in files
    assert "ai_agent/openai_tool_bridge.py" in files


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
    assert any("test_editor_advisor_tools.py" in command for command in commands)
    assert any("test_editor_offset_characterization.py" in command for command in commands)
    assert any("static/js/editor_offset_visual/api_client.js" in command for command in commands)
    assert all("rm " not in command.lower() for command in commands)


def test_architecture_summary_reports_post_5b_services_and_ai_split():
    summary = tools.summarize_editor_architecture()

    assert "services/editor_offset_http_service.py" in summary
    assert "services/editor_offset_output_service.py" in summary
    assert "Wrapper legacy de salida: montaje_offset_inteligente.py" in summary
    assert "static/js/editor_offset_visual/api_client.js" in summary
    assert "ai_agent/tools_repeat.py" in summary
    assert "ai_agent/openai_tool_bridge.py" in summary
    assert "Advisor SDK" in summary
    assert "CLI-only/read-only" in summary


def test_modular_surface_summary_reports_5a_5b_and_pending_risks():
    summary = tools.summarize_editor_modular_surface()

    assert "Mapa modular post Fases 5A/5B" in summary
    assert "Modulos esperados presentes en disco: 9/9" in summary
    assert "Modulos esperados cargados en HTML: 9/9" in summary
    assert "dom_refs.js -> domRefs" in summary
    assert "api_client.js -> apiClient" in summary
    assert "booklet_panel.js -> bookletPanel" in summary
    assert "Entry point compatible: static/js/editor_offset_visual.js" in summary
    assert "renderSheet" in summary
    assert "box select" in summary
    assert "Fase 5C pendiente" in summary
    assert "Fase 5D pendiente" in summary
    assert "Fase 6 pendiente" in summary
    assert "Los 9 modulos esperados 5A/5B estan presentes" in summary


def test_ux_surface_summary_reports_right_panel_signals():
    summary = tools.summarize_editor_ux_surface()

    assert "Superficie UX del Editor Visual IA" in summary
    assert "Tabs del panel derecho" in summary
    assert "editor-tab-panels" in summary
    assert "geometry-validation-panel" in summary
    assert "getElementById" in summary
    assert "Listeners detectados en JS: 91" in summary
    assert "no renombrar ids" in summary


def test_ux_surface_summary_reports_canvas_pro_shell_signals():
    summary = tools.summarize_editor_ux_surface()

    assert "Header/topbar/subtoolbar" in summary
    assert ".editor-header" in summary
    assert ".editor-topbar" in summary
    assert ".sheet-subtoolbar" in summary
    assert "Workspace principal" in summary
    assert "editor-workspace" in summary
    assert "Canvas/sheet/zoom" in summary
    assert "sheet-canvas" in summary
    assert "zoom-in" in summary
    assert "Geometry panel" in summary
    assert "geometry-validation-panel" in summary
    assert "no duplicar geometry-validation-panel" in summary
    assert "compactar botones" in summary
    assert "preferir CSS-only" in summary
    assert "no cambiar data-editor-tab/data-editor-tab-panel" in summary


def test_ux_surface_summary_reports_listener_risk_groups():
    summary = tools.summarize_editor_ux_surface()

    assert "IDs topbar/cara detectados" in summary
    assert "btn-save" in summary
    assert "face-front" in summary
    assert "IDs snap/spacing detectados" in summary
    assert "snap-slots" in summary
    assert "spacing-x" in summary
    assert "IDs edicion rapida detectados" in summary
    assert "btn-nudge-up" in summary
    assert "IDs con listeners sensibles para Fase 10" in summary
    assert "btn-preview" in summary
    assert "btn-pdf" in summary


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
    assert report.prompt_para_codex == ""


def test_editor_advisor_report_accepts_multiline_codex_prompt():
    prompt = (
        "Objetivo de la fase:\n"
        "- Mejorar el asesor.\n\n"
        "Antes de implementar, dame un plan SAFE."
    )
    report = EditorAdvisorReport(prompt_para_codex=prompt)

    assert report.prompt_para_codex == prompt


def test_cli_formats_codex_prompt_only_without_json():
    report = EditorAdvisorReport(
        prompt_para_codex="Objetivo de la fase:\n- Preparar una fase SAFE."
    )

    output = _format_report_output(report, codex_prompt_only=True)

    assert output.startswith("Objetivo de la fase:")
    assert "prompt_para_codex" not in output


def test_cli_rejects_empty_codex_prompt_only():
    report = EditorAdvisorReport()

    with pytest.raises(ValueError, match="prompt_para_codex"):
        _format_report_output(report, codex_prompt_only=True)
