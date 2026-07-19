from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from editor_offset_v2.domain.validation import validate_layout_v2


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_javascript_development_placeholder_satisfies_layout_v2_contract():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to validate the Phase 5 frontend placeholder")

    script = r"""
const fs = require("node:fs");
const commands = require("./static/js/editor_offset_v2/commands.js");
const layout = JSON.parse(fs.readFileSync(
  "./tests/fixtures/editor_offset_v2/layout_v2_minimal.json",
  "utf8",
));
const bundle = commands.createDevelopmentPlaceholderBundle(
  layout,
  "python_contract",
  "2026-07-19T00:00:00Z",
);
layout.assets.push(bundle.asset);
layout.works.push(bundle.work);
layout.slots.push(bundle.slot);
process.stdout.write(JSON.stringify(layout));
"""
    completed = subprocess.run(
        [node, "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    layout = json.loads(completed.stdout)

    assert validate_layout_v2(layout) == []
    assert layout["assets"][0]["status"] == "error"
    assert layout["assets"][0]["pages"][0]["preflight"]["issues"][0]["code"] == (
        "DEVELOPMENT_PLACEHOLDER"
    )
    assert layout["slots"][0]["generated_by"]["type"] == "manual"
