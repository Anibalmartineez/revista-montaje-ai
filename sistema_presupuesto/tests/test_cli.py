import json
from io import StringIO
from pathlib import Path

from sistema_presupuesto.cli import run

ROOT = Path(__file__).resolve().parents[1]


def fixture_path(name):
    return str(ROOT / "data" / "fixtures" / name)


def copy_catalogs(tmp_path):
    catalog_dir = tmp_path / "catalogo"
    catalog_dir.mkdir(parents=True)
    source_dir = ROOT / "data" / "catalogo"
    for source in source_dir.glob("*.json"):
        (catalog_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def run_cli(args):
    stdout = StringIO()
    stderr = StringIO()
    code = run(args, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_cli_calcular_valid_fixture():
    code, stdout, stderr = run_cli(["calcular", fixture_path("quote_request_volante.json")])

    assert code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert payload["result"]["request_fixture_id"] == "quote_request_volante"
    assert payload["result"]["costos"]["precio_final"]


def test_cli_fails_with_missing_input_file():
    code, stdout, stderr = run_cli(["calcular", "no_existe.json"])

    assert code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "FileNotFoundError"


def test_cli_fails_with_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{bad json", encoding="utf-8")

    code, stdout, stderr = run_cli(["calcular", str(bad_file)])

    assert code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "JSONDecodeError"


def test_cli_calcular_y_guardar_then_listar_and_ver(tmp_path):
    copy_catalogs(tmp_path)

    code, stdout, stderr = run_cli(
        [
            "--data-dir",
            str(tmp_path),
            "calcular-y-guardar",
            fixture_path("quote_request_volante.json"),
        ]
    )

    assert code == 0
    assert stderr == ""
    saved = json.loads(stdout)
    presupuesto_id = saved["presupuesto_id"]
    assert (tmp_path / "presupuestos" / f"{presupuesto_id}.json").exists()

    code, stdout, stderr = run_cli(["--data-dir", str(tmp_path), "listar"])
    assert code == 0
    listed = json.loads(stdout)
    assert listed["presupuestos"][0]["presupuesto_id"] == presupuesto_id

    code, stdout, stderr = run_cli(["--data-dir", str(tmp_path), "ver", presupuesto_id])
    assert code == 0
    viewed = json.loads(stdout)
    assert viewed["record"]["presupuesto_id"] == presupuesto_id


def test_cli_reports_missing_catalog(tmp_path):
    code, stdout, stderr = run_cli(
        [
            "--data-dir",
            str(tmp_path),
            "calcular",
            fixture_path("quote_request_volante.json"),
        ]
    )

    assert code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "JsonFileNotFoundError"

