from pathlib import Path

from PIL import Image, ImageDraw

from pdf_medidor_pro.services.ai_measure_engine import (
    count_label_candidates,
    detect_measurement_near,
    detect_printed_measurement,
)


def make_image(path: Path) -> Path:
    image = Image.new("RGB", (200, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 30, 89, 69), fill="black")
    draw.rectangle((120, 30, 159, 59), fill="black")
    image.save(path)
    return path


def test_detect_measurement_near_returns_mm_bbox(tmp_path):
    path = make_image(tmp_path / "labels.png")

    result = detect_measurement_near(
        path,
        x_mm=25,
        y_mm=25,
        render_mm={"ancho": 100, "alto": 60},
        name="Etiqueta (IA)",
    )

    assert result is not None
    assert result["origen"] == "ia"
    assert result["nombre"] == "Etiqueta (IA)"
    assert 20 <= result["ancho_mm"] <= 30
    assert 18 <= result["alto_mm"] <= 25
    assert result["area_mm2"] > 0
    assert result["perimetro_mm"] > 0
    assert result["confianza"] > 0


def test_detect_printed_measurement_returns_union(tmp_path):
    path = make_image(tmp_path / "labels.png")

    result = detect_printed_measurement(path, render_mm={"ancho": 100, "alto": 60})

    assert result is not None
    assert result["nombre"] == "Area impresa (IA)"
    assert result["ancho_mm"] > 50
    assert result["alto_mm"] > 10


def test_count_label_candidates(tmp_path):
    path = make_image(tmp_path / "labels.png")

    result = count_label_candidates(path)

    assert result["count"] == 2
    assert "objetos candidatos" in result["message"]
