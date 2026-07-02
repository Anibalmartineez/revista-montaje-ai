import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE_SCRIPT = ROOT / "static" / "js" / "guides.js"


def run_node(source: str):
    script = f"""
const guides = require({json.dumps(str(NODE_SCRIPT))});
{source}
"""
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_create_and_normalize_guides_keep_compatible_position_fields():
    result = run_node(
        """
const vertical = guides.createGuide("vertical", 12.3456);
const legacy = guides.normalizeGuide({id: "old", orientation: "horizontal", value_mm: 22.2222});
console.log(JSON.stringify({vertical, legacy}));
"""
    )

    assert result["vertical"]["type"] == "guide"
    assert result["vertical"]["orientation"] == "vertical"
    assert result["vertical"]["position_mm"] == 12.346
    assert result["vertical"]["value_mm"] == 12.346
    assert result["legacy"]["position_mm"] == 22.222
    assert result["legacy"]["value_mm"] == 22.222


def test_move_replace_and_delete_guide():
    result = run_node(
        """
const guide = guides.createGuide("horizontal", 10);
const moved = guides.moveGuide(guide, 18.5);
const replaced = guides.replaceGuide([guide], moved);
console.log(JSON.stringify({
  moved,
  replaced,
  deleted: guides.deleteGuide(replaced, guide.id)
}));
"""
    )

    assert result["moved"]["position_mm"] == 18.5
    assert result["moved"]["value_mm"] == 18.5
    assert result["replaced"][0]["position_mm"] == 18.5
    assert result["deleted"] == []


def test_guide_snap_candidates_use_position_mm_and_ignore_hidden_guides():
    result = run_node(
        """
const candidates = guides.guideSnapCandidates([
  {id: "gv", type: "guide", orientation: "vertical", position_mm: 30, visible: true},
  {id: "gh", type: "guide", orientation: "horizontal", position_mm: 40, visible: false}
], {ancho: 100, alto: 200});
console.log(JSON.stringify(candidates));
"""
    )

    assert {item["kind"] for item in result} == {"guia_vertical", "guia_vertical_centro"}
    assert all(item["source_id"] == "gv" for item in result)
