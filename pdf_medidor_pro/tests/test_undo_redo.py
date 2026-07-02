import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE_SCRIPT = ROOT / "static" / "js" / "undo_redo.js"


def run_node(source: str):
    script = f"""
const undoRedo = require({json.dumps(str(NODE_SCRIPT))});
{source}
"""
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_undo_and_redo_restore_snapshots():
    result = run_node(
        """
const history = undoRedo.createHistory(50);
const empty = {measurements: [], selectedMeasurementId: null, finalMeasurementId: null, finalOrigin: "auto", finalConfidence: "media"};
const withLine = {measurements: [{id: "m1", tipo: "linea"}], selectedMeasurementId: "m1", finalMeasurementId: null, finalOrigin: "auto", finalConfidence: "media"};
history.capture(empty);
const undone = history.undo(withLine);
const redone = history.redo(undone);
console.log(JSON.stringify({undone, redone, sizes: history.sizes()}));
"""
    )

    assert result["undone"]["measurements"] == []
    assert result["redone"]["measurements"][0]["id"] == "m1"
    assert result["sizes"] == {"undo": 1, "redo": 0}


def test_new_capture_clears_redo_stack():
    result = run_node(
        """
const history = undoRedo.createHistory(50);
const a = {measurements: [], selectedMeasurementId: null, finalMeasurementId: null, finalOrigin: "auto", finalConfidence: "media"};
const b = {measurements: [{id: "a"}], selectedMeasurementId: "a", finalMeasurementId: null, finalOrigin: "auto", finalConfidence: "media"};
const c = {measurements: [{id: "b"}], selectedMeasurementId: "b", finalMeasurementId: null, finalOrigin: "auto", finalConfidence: "media"};
history.capture(a);
history.undo(b);
history.capture(c);
console.log(JSON.stringify({canRedo: history.canRedo(), sizes: history.sizes()}));
"""
    )

    assert result["canRedo"] is False
    assert result["sizes"]["redo"] == 0


def test_history_keeps_maximum_50_states():
    result = run_node(
        """
const history = undoRedo.createHistory(50);
for (let i = 0; i < 60; i += 1) {
  history.capture({measurements: [{id: String(i)}], selectedMeasurementId: String(i), finalMeasurementId: null, finalOrigin: "auto", finalConfidence: "media"});
}
console.log(JSON.stringify(history.sizes()));
"""
    )

    assert result["undo"] == 50
    assert result["redo"] == 0


def test_empty_history_does_not_throw():
    result = run_node(
        """
const history = undoRedo.createHistory(50);
const current = {measurements: [{id: "m1"}], selectedMeasurementId: "m1", finalMeasurementId: null, finalOrigin: "auto", finalConfidence: "media"};
console.log(JSON.stringify({undo: history.undo(current), redo: history.redo(current), sizes: history.sizes()}));
"""
    )

    assert result["undo"]["measurements"][0]["id"] == "m1"
    assert result["redo"]["measurements"][0]["id"] == "m1"
    assert result["sizes"] == {"undo": 0, "redo": 0}


def test_guides_are_reversible_internal_state():
    result = run_node(
        """
const history = undoRedo.createHistory(50);
const empty = {measurements: [], guides: [], selectedGuideId: null};
const withGuide = {measurements: [], guides: [{id: "g1", type: "guide", orientation: "vertical", position_mm: 12}], selectedGuideId: "g1"};
history.capture(empty);
const undone = history.undo(withGuide);
const redone = history.redo(undone);
console.log(JSON.stringify({undone, redone}));
"""
    )

    assert result["undone"]["guides"] == []
    assert result["undone"]["selectedGuideId"] is None
    assert result["redone"]["guides"][0]["id"] == "g1"
    assert result["redone"]["selectedGuideId"] == "g1"
