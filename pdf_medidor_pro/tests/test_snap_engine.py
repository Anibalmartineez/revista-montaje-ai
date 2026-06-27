from pdf_medidor_pro.services.snap_engine import snap_point


def test_snap_point_returns_nearest_candidate():
    measurements = [
        {
            "id": "r1",
            "tipo": "rectangulo",
            "x_mm": 10,
            "y_mm": 20,
            "ancho_mm": 30,
            "alto_mm": 40,
        }
    ]

    result = snap_point({"x_mm": 10.4, "y_mm": 20.3}, measurements)

    assert result["snapped"] is True
    assert result["point"] == {"x_mm": 10, "y_mm": 20}
    assert result["candidate"]["kind"] == "esquina_sup_izq"


def test_snap_point_respects_disabled_toggle():
    result = snap_point(
        {"x_mm": 10.4, "y_mm": 20.3},
        [{"id": "l1", "tipo": "linea", "a": {"x_mm": 10, "y_mm": 20}, "b": {"x_mm": 50, "y_mm": 20}}],
        enabled=False,
    )

    assert result["snapped"] is False
    assert result["point"] == {"x_mm": 10.4, "y_mm": 20.3}


def test_snap_point_strict_threshold_is_smaller():
    measurements = [{"id": "l1", "tipo": "linea", "a": {"x_mm": 10, "y_mm": 20}, "b": {"x_mm": 50, "y_mm": 20}}]

    loose = snap_point({"x_mm": 11.2, "y_mm": 20}, measurements)
    strict = snap_point({"x_mm": 11.2, "y_mm": 20}, measurements, strict=True)

    assert loose["snapped"] is True
    assert strict["snapped"] is False
