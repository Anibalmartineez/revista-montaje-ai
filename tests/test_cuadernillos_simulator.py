from pathlib import Path
import os
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OPENAI_API_KEY", "test")

import pytest

from app import app
from cuadernillos.simulator import (
    CuadernilloSimulationError,
    _cuadernillo_8,
    _cuadernillo_16,
    _vyv_4,
    _vyv_8,
    simular_cuadernillo,
)


def _payload(
    total_paginas,
    tipo="cosido_caballete",
    tipo_tapa="sin_tapa",
    tipo_cuadernillo=8,
):
    return {
        "total_paginas": total_paginas,
        "tipo_encuadernacion": tipo,
        "tipo_tapa": tipo_tapa,
        "tipo_cuadernillo": tipo_cuadernillo,
    }


def test_simular_cuadernillo_16_paginas():
    result = simular_cuadernillo(_payload(16))

    assert result["total_paginas_original"] == 16
    assert result["total_paginas_final"] == 16
    assert result["blancas_agregadas"] == 0
    assert len(result["pliegos"]) == 2
    assert result["pliegos"][0]["pliego"] == 1
    assert result["pliegos"][0]["tipo"] == "cuadernillo_8"
    assert result["pliegos"][0]["modo"] == "cuadernillo_8"
    assert result["pliegos"][0]["paginas_por_cara"] == 4
    assert result["pliegos"][0]["frente"] == [16, 13, 1, 4]
    assert result["pliegos"][0]["dorso"] == [14, 15, 3, 2]
    assert result["pliegos"][1]["pliego"] == 2
    assert result["pliegos"][1]["tipo"] == "cuadernillo_8"
    assert result["pliegos"][1]["modo"] == "cuadernillo_8"
    assert result["pliegos"][1]["paginas_por_cara"] == 4
    assert result["pliegos"][1]["frente"] == [12, 9, 5, 8]
    assert result["pliegos"][1]["dorso"] == [10, 11, 7, 6]


def test_simular_cuadernillo_24_paginas():
    result = simular_cuadernillo(_payload(24))

    assert result["total_paginas_final"] == 24
    assert len(result["pliegos"]) == 3
    assert result["pliegos"][0]["frente"] == [24, 21, 1, 4]
    assert result["pliegos"][2]["dorso"] == [14, 15, 11, 10]


def test_simular_cuadernillo_30_paginas_normaliza_a_32():
    result = simular_cuadernillo(_payload(30))

    assert result["total_paginas_original"] == 30
    assert result["total_paginas_final"] == 32
    assert result["blancas_agregadas"] == 2
    assert len(result["pliegos"]) == 4
    assert result["pliegos"][0]["pliego"] == 1
    assert result["pliegos"][0]["tipo"] == "cuadernillo_8"
    assert result["pliegos"][0]["modo"] == "cuadernillo_8"
    assert result["pliegos"][0]["paginas_por_cara"] == 4
    assert result["pliegos"][0]["frente"] == [32, 29, 1, 4]
    assert result["pliegos"][0]["dorso"] == [30, 31, 3, 2]


def test_simular_cuadernillo_32_paginas_sin_tapa_conserva_logica_actual():
    result = simular_cuadernillo(_payload(32, tipo_tapa="sin_tapa"))

    assert result["tipo_tapa"] == "sin_tapa"
    assert result["total_paginas_final"] == 32
    assert result["pliegos"][0]["pliego"] == 1
    assert result["pliegos"][0]["tipo"] == "cuadernillo_8"
    assert result["pliegos"][0]["modo"] == "cuadernillo_8"
    assert result["pliegos"][0]["paginas_por_cara"] == 4
    assert result["pliegos"][0]["frente"] == [32, 29, 1, 4]
    assert result["pliegos"][0]["dorso"] == [30, 31, 3, 2]


def test_simular_cuadernillo_32_paginas_tapa_completa():
    result = simular_cuadernillo(_payload(32, tipo_tapa="tapa_completa"))

    assert result["tipo_tapa"] == "tapa_completa"
    assert result["tapa"]["modo"] == "vyv_4_tapa"
    assert result["tapa"]["cara"] == [32, 31, 1, 2]
    assert result["tripa"]["paginas_inicio"] == 3
    assert result["tripa"]["paginas_fin"] == 30
    assert result["tripa"]["paginas_original"] == 28
    assert result["tripa"]["paginas_final"] == 28
    assert result["tripa"]["pliegos"][0]["frente"] == [30, 27, 3, 6]
    assert result["tripa"]["pliegos"][0]["dorso"] == [28, 29, 5, 4]
    assert result["tripa"]["pliegos"][0]["modo"] == "cuadernillo_8"
    assert result["tripa"]["pliegos"][0]["paginas_por_cara"] == 4
    assert result["pliegos"] == result["tripa"]["pliegos"]


def test_simular_cuadernillo_24_paginas_tapa_completa():
    result = simular_cuadernillo(_payload(24, tipo_tapa="tapa_completa"))

    assert result["tapa"]["cara"] == [24, 23, 1, 2]
    assert result["tripa"]["paginas_inicio"] == 3
    assert result["tripa"]["paginas_fin"] == 22
    assert result["tripa"]["paginas_original"] == 20
    assert result["tripa"]["pliegos"][0]["frente"] == [22, 19, 3, 6]


def test_simular_cuadernillo_30_paginas_tapa_completa_normaliza_a_32():
    result = simular_cuadernillo(_payload(30, tipo_tapa="tapa_completa"))

    assert result["total_paginas_original"] == 30
    assert result["total_paginas_final"] == 32
    assert result["blancas_agregadas"] == 2
    assert result["tapa"]["cara"] == [32, 31, 1, 2]


def test_simular_cuadernillo_pliegos_normales_y_parcial_declaran_paginas_por_cara():
    result = simular_cuadernillo(
        _payload(28, tipo_tapa="tapa_completa", tipo_cuadernillo=16)
    )
    normal = result["tripa"]["pliegos"][0]
    parcial = result["tripa"]["pliegos"][-1]

    assert normal["tipo"] == "cuadernillo_16"
    assert normal["paginas_por_cara"] == 8
    assert parcial["tipo"] == "vyv_8"
    assert parcial["paginas_por_cara"] == 8
    assert "cara" in parcial
    assert "frente" not in parcial
    assert "dorso" not in parcial


def test_revista_36_paginas_tapa_completa_cuadernillo_16_usa_extremos():
    result = simular_cuadernillo(
        _payload(36, tipo_tapa="tapa_completa", tipo_cuadernillo=16)
    )

    pliegos = result["tripa"]["pliegos"]
    assert len(pliegos) == 2
    assert pliegos[0]["tipo"] == "cuadernillo_16"
    assert pliegos[0]["paginas_por_cara"] == 8
    assert pliegos[0]["frente"] == [7, 30, 27, 10, 6, 31, 34, 3]
    assert pliegos[0]["dorso"] == [9, 28, 29, 8, 4, 33, 32, 5]
    assert pliegos[1]["frente"] == [15, 22, 19, 18, 14, 23, 26, 11]


def test_tapa_completa_36_es_vyv_4_cara_unica():
    result = simular_cuadernillo(
        _payload(36, tipo_tapa="tapa_completa", tipo_cuadernillo=16)
    )
    tapa = result["tapa"]

    assert tapa["paginas"] == [36, 1, 2, 35]
    assert tapa["modo"] == "vyv_4_tapa"
    assert tapa["paginas_por_cara"] == 4
    assert tapa["cara"] == [36, 35, 1, 2]
    assert [item["pagina"] for item in tapa["cara_visual"]] == [36, 35, 1, 2]
    assert [item["rotacion"] for item in tapa["cara_visual"]] == [90, -90, 90, -90]
    assert result["tripa"]["paginas_inicio"] == 3
    assert result["tripa"]["paginas_fin"] == 34


def test_paginas_por_cara_de_entrada_se_ignora_y_se_deriva():
    payload = _payload(36, tipo_tapa="tapa_completa", tipo_cuadernillo=16)
    payload["paginas_por_cara"] = 4

    result = simular_cuadernillo(payload)

    assert result["paginas_por_cara"] == 8
    assert result["tripa"]["pliegos"][0]["paginas_por_cara"] == 8


def test_revista_28_paginas_tapa_completa_cuadernillo_16_genera_vyv_8():
    result = simular_cuadernillo(
        _payload(28, tipo_tapa="tapa_completa", tipo_cuadernillo=16)
    )

    ultimo = result["tripa"]["pliegos"][-1]
    assert ultimo["tipo"] == "vyv_8"
    assert ultimo["modo"] == "vyv_8_paginas"
    assert ultimo["paginas_por_cara"] == 8
    assert ultimo["cara"] == [18, 11, 16, 13, 14, 15, 12, 17]


def test_revista_20_paginas_sin_tapa_cuadernillo_16_genera_vyv_4():
    result = simular_cuadernillo(_payload(20, tipo_cuadernillo=16))

    ultimo = result["pliegos"][-1]
    assert ultimo["tipo"] == "vyv_4"
    assert ultimo["modo"] == "vyv_4_paginas"
    assert ultimo["paginas_por_cara"] == 4
    assert ultimo["cara"] == [12, 9, 10, 11]


def test_revista_24_paginas_tapa_completa_cuadernillo_16_genera_vyv_4():
    result = simular_cuadernillo(
        _payload(24, tipo_tapa="tapa_completa", tipo_cuadernillo=16)
    )

    ultimo = result["tripa"]["pliegos"][-1]
    assert ultimo["tipo"] == "vyv_4"
    assert ultimo["cara"] == [14, 11, 12, 13]


def test_patron_cuadernillo_8_paginas_logicas():
    pliego = _cuadernillo_8(1, list(range(1, 9)))

    assert pliego["frente"] == [8, 5, 1, 4]
    assert pliego["dorso"] == [6, 7, 3, 2]


def test_patron_cuadernillo_16_paginas_logicas():
    pliego = _cuadernillo_16(1, list(range(1, 17)))

    assert pliego["frente"] == [5, 12, 9, 8, 4, 13, 16, 1]
    assert pliego["dorso"] == [7, 10, 11, 6, 2, 15, 14, 3]


def test_patron_vyv_4_usa_cara_unica_derivada_de_cuadernillo_8():
    pliego = _vyv_4(1, [1, 2, 3, 4])

    assert pliego["cara"] == [4, 1, 2, 3]
    assert "frente" not in pliego
    assert "dorso" not in pliego


def test_patron_vyv_8_usa_cara_unica_derivada_de_cuadernillo_16():
    pliego = _vyv_8(1, list(range(1, 9)))

    assert pliego["cara"] == [8, 1, 6, 3, 4, 5, 2, 7]
    assert "frente" not in pliego
    assert "dorso" not in pliego


def test_cuadernillo_8_incluye_visual_cabeza_con_cabeza():
    pliego = _cuadernillo_8(1, list(range(1, 9)))

    assert pliego["frente_visual"] == [
        {"pagina": 8, "rotacion": 90},
        {"pagina": 5, "rotacion": -90},
        {"pagina": 1, "rotacion": 90},
        {"pagina": 4, "rotacion": -90},
    ]
    assert [item["rotacion"] for item in pliego["dorso_visual"]] == [90, -90, 90, -90]


def test_cuadernillo_16_incluye_visual_cabeza_con_cabeza():
    pliego = _cuadernillo_16(1, list(range(1, 17)))

    assert "frente_visual" in pliego
    assert "dorso_visual" in pliego
    assert [item["pagina"] for item in pliego["frente_visual"]] == pliego["frente"]
    assert [item["rotacion"] for item in pliego["frente_visual"]] == [
        180,
        180,
        180,
        180,
        0,
        0,
        0,
        0,
    ]


def test_vyv_incluye_cara_visual_cabeza_con_cabeza():
    vyv_4 = _vyv_4(1, [1, 2, 3, 4])
    vyv_8 = _vyv_8(1, list(range(1, 9)))

    assert [item["pagina"] for item in vyv_4["cara_visual"]] == vyv_4["cara"]
    assert [item["rotacion"] for item in vyv_4["cara_visual"]] == [90, -90, 90, -90]
    assert [item["pagina"] for item in vyv_8["cara_visual"]] == vyv_8["cara"]
    assert [item["rotacion"] for item in vyv_8["cara_visual"]] == [
        180,
        180,
        180,
        180,
        0,
        0,
        0,
        0,
    ]


def test_simular_cuadernillo_tipo_tapa_no_soportado_error_claro():
    with pytest.raises(CuadernilloSimulationError, match="Tipo de tapa no soportado"):
        simular_cuadernillo(_payload(16, tipo_tapa="tapa_simple"))


def test_simular_cuadernillo_modo_no_soportado_error_claro():
    with pytest.raises(CuadernilloSimulationError, match="Modo no soportado"):
        simular_cuadernillo(_payload(16, tipo="wire_o"))


def test_ruta_cuadernillos_modo_no_soportado_devuelve_error():
    client = app.test_client()
    res = client.post("/editor_offset/cuadernillos/simular", json=_payload(16, tipo="wire_o"))
    data = res.get_json()

    assert res.status_code == 422
    assert data["ok"] is False
    assert "Modo no soportado" in data["error"]
