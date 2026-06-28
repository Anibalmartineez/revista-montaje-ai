import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE_SCRIPT = ROOT / "static" / "js" / "object_model.js"


def run_node(source: str):
    script = f"""
const model = require({json.dumps(str(NODE_SCRIPT))});
{source}
"""
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_move_object_moves_line_and_rectangle():
    result = run_node(
        """
const line = model.createLine({x_mm: 1, y_mm: 2}, {x_mm: 11, y_mm: 12});
const rect = model.createRectangle({x_mm: 5, y_mm: 5}, {x_mm: 15, y_mm: 25});
console.log(JSON.stringify({
  line: model.moveObject(line, 3, -2),
  rect: model.moveObject(rect, -1, 4)
}));
"""
    )

    assert result["line"]["a"] == {"x_mm": 4, "y_mm": 0}
    assert result["line"]["b"] == {"x_mm": 14, "y_mm": 10}
    assert result["rect"]["x_mm"] == 4
    assert result["rect"]["y_mm"] == 9


def test_resize_rectangle_from_handle():
    result = run_node(
        """
const rect = model.createRectangle({x_mm: 10, y_mm: 10}, {x_mm: 30, y_mm: 40});
console.log(JSON.stringify(model.resizeRectangle(rect, "se", {x_mm: 45, y_mm: 55})));
"""
    )

    assert result["ancho_mm"] == 35
    assert result["alto_mm"] == 45


def test_delete_rename_color_visible_and_duplicate():
    result = run_node(
        """
const rect = model.createRectangle({x_mm: 0, y_mm: 0}, {x_mm: 10, y_mm: 20}, {id: "r1"});
const renamed = model.renameObject(rect, "Caja final");
const colored = model.setObjectColor(renamed, "#ff0000");
const hidden = model.setObjectVisible(colored, false);
const duplicated = model.duplicateObject(hidden);
console.log(JSON.stringify({
  hidden,
  duplicated,
  remaining: model.deleteObject([hidden, duplicated], "r1")
}));
"""
    )

    assert result["hidden"]["nombre"] == "Caja final"
    assert result["hidden"]["color"] == "#ff0000"
    assert result["hidden"]["visible"] is False
    assert result["duplicated"]["x_mm"] == 5
    assert len(result["remaining"]) == 1


def test_shift_angle_constraint_locks_to_common_angles():
    result = run_node(
        """
console.log(JSON.stringify(model.constrainLineAngle({x_mm: 0, y_mm: 0}, {x_mm: 10, y_mm: 2})));
"""
    )

    assert result["y_mm"] == 0


def test_nudge_precision_uses_exact_mm_steps():
    result = run_node(
        """
const line = model.createLine({x_mm: 1, y_mm: 2}, {x_mm: 3, y_mm: 4});
const rect = model.createRectangle({x_mm: 10, y_mm: 10}, {x_mm: 20, y_mm: 20});
console.log(JSON.stringify({
  lineFine: model.moveObject(line, 0.01, 0),
  rectNormal: model.moveObject(rect, 0, -0.1),
  rectShift: model.moveObject(rect, 1, 0)
}));
"""
    )

    assert result["lineFine"]["a"]["x_mm"] == 1.01
    assert result["lineFine"]["b"]["x_mm"] == 3.01
    assert result["rectNormal"]["y_mm"] == 9.9
    assert result["rectShift"]["x_mm"] == 11
