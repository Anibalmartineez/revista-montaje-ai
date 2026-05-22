import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ai_agent.editor_advisor import tools


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
