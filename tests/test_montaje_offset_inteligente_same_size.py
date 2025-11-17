import sys
from pathlib import Path

from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))

from montaje_offset_inteligente import montar_pliego_offset_inteligente


def test_montaje_offset_inteligente_same_size(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "montaje_offset_inteligente.obtener_dimensiones_pdf",
        lambda path, usar_trimbox=False: (50.0, 30.0),
    )

    monkeypatch.setattr(
        "montaje_offset_inteligente._pdf_a_imagen_con_sangrado",
        lambda path, sangrado_mm, usar_trimbox=False: Image.new("RGB", (100, 60), color="white"),
    )

    def _fake_preview(disenos, positions, hoja_ancho_mm, hoja_alto_mm, preview_path):
        img = Image.new("RGB", (10, 10), color="white")
        img.save(preview_path)

    monkeypatch.setattr(
        "montaje_offset_inteligente.generar_preview_pliego",
        _fake_preview,
    )

    disenos = [
        ("/fake/path/parmalat.pdf", 3),
        ("/fake/path/cliente_b.pdf", 2),
        ("/fake/path/cliente_c.pdf", 1),
    ]

    output_pdf = tmp_path / "test_same_size.pdf"

    res = montar_pliego_offset_inteligente(
        disenos,
        ancho_pliego=640.0,
        alto_pliego=880.0,
        sangrado=3.0,
        separacion=4.0,
        estrategia="flujo",
        devolver_posiciones=True,
        preview_only=True,
        output_path=str(output_pdf),
    )

    assert isinstance(res, dict)
    assert "positions" in res and "sheet_mm" in res

    archivos = [p["archivo"] for p in res["positions"]]
    assert any("parmalat.pdf" in a for a in archivos)
    assert any("cliente_b.pdf" in a for a in archivos)
    assert any("cliente_c.pdf" in a for a in archivos)

    idxs_por_archivo = {}
    for p in res["positions"]:
        idxs_por_archivo.setdefault(p["archivo"], set()).add(p["file_idx"])

    assert idxs_por_archivo["/fake/path/parmalat.pdf"] == {0}
    assert idxs_por_archivo["/fake/path/cliente_b.pdf"] == {1}
    assert idxs_por_archivo["/fake/path/cliente_c.pdf"] == {2}
