from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = "a" + "i"


DELETED_FILES = [
    f"services/{AI}_measure_engine.py",
    "services/object_" + "detector.py",
    f"static/js/{AI}_measure.js",
    f"static/js/commands_{AI}.js",
    f"tests/test_{AI}_measure_engine.py",
    "docs/05_COMANDOS_" + "IA.md",
    "docs/04_FASE_2_ZOOM_LUPA_" + "IA.md",
]

FORBIDDEN_TEXT = [
    f"/api/pdf-medidor-pro/{AI}/",
    f"{AI}_measure.js",
    f"commands_{AI}.js",
    f"{AI}_measure_engine",
    "object_" + "detector",
    "Medir con " + "IA",
    "Etiqueta (" + "IA)",
    "Objeto detectado (" + "IA)",
    '"origen": "' + AI + '"',
    '"origen_medida_final": "' + AI + '"',
]


def test_ai_files_were_removed():
    for relative_path in DELETED_FILES:
        assert not (ROOT / relative_path).exists()


def test_no_functional_ai_references_remain():
    searchable = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".py", ".js", ".html", ".md"}
        and path.name != "test_no_ai_references.py"
        and "__pycache__" not in path.parts
    ]

    haystack = "\n".join(path.read_text(encoding="utf-8") for path in searchable)

    for forbidden in FORBIDDEN_TEXT:
        assert forbidden not in haystack
