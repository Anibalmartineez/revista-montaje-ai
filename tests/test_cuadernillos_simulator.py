from pathlib import Path
import os
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OPENAI_API_KEY", "test")

import pytest

from app import app
from cuadernillos.simulator import CuadernilloSimulationError, simular_cuadernillo


def _payload(
    total_paginas,
    tipo="cosido_caballete",
    paginas_por_cara=4,
    tipo_tapa="sin_tapa",
):
    return {
        "total_paginas": total_paginas,
        "tipo_encuadernacion": tipo,
        "paginas_por_cara": paginas_por_cara,
        "tipo_tapa": tipo_tapa,
    }


def test_simular_cuadernillo_16_paginas():
    result = simular_cuadernillo(_payload(16))

    assert result["total_paginas_original"] == 16
    assert result["total_paginas_final"] == 16
    assert result["blancas_agregadas"] == 0
    assert result["pliegos"] == [
        {
            "pliego": 1,
            "modo": "normal_4_por_cara",
            "paginas_por_cara": 4,
            "frente": [16, 1, 14, 3],
            "dorso": [2, 15, 4, 13],
        },
        {
            "pliego": 2,
            "modo": "normal_4_por_cara",
            "paginas_por_cara": 4,
            "frente": [12, 5, 10, 7],
            "dorso": [6, 11, 8, 9],
        },
    ]


def test_simular_cuadernillo_24_paginas():
    result = simular_cuadernillo(_payload(24))

    assert result["total_paginas_final"] == 24
    assert len(result["pliegos"]) == 3
    assert result["pliegos"][0]["frente"] == [24, 1, 22, 3]
    assert result["pliegos"][2]["dorso"] == [10, 15, 12, 13]


def test_simular_cuadernillo_30_paginas_normaliza_a_32():
    result = simular_cuadernillo(_payload(30))

    assert result["total_paginas_original"] == 30
    assert result["total_paginas_final"] == 32
    assert result["blancas_agregadas"] == 2
    assert len(result["pliegos"]) == 4
    assert result["pliegos"][0] == {
        "pliego": 1,
        "modo": "normal_4_por_cara",
        "paginas_por_cara": 4,
        "frente": [32, 1, 30, 3],
        "dorso": [2, 31, 4, 29],
    }


def test_simular_cuadernillo_32_paginas_sin_tapa_conserva_logica_actual():
    result = simular_cuadernillo(_payload(32, tipo_tapa="sin_tapa"))

    assert result["tipo_tapa"] == "sin_tapa"
    assert result["total_paginas_final"] == 32
    assert result["pliegos"][0] == {
        "pliego": 1,
        "modo": "normal_4_por_cara",
        "paginas_por_cara": 4,
        "frente": [32, 1, 30, 3],
        "dorso": [2, 31, 4, 29],
    }


def test_simular_cuadernillo_32_paginas_tapa_completa():
    result = simular_cuadernillo(_payload(32, tipo_tapa="tapa_completa"))

    assert result["tipo_tapa"] == "tapa_completa"
    assert result["tapa"]["frente"] == [32, 1]
    assert result["tapa"]["dorso"] == [2, 31]
    assert result["tripa"]["paginas_inicio"] == 3
    assert result["tripa"]["paginas_fin"] == 30
    assert result["tripa"]["paginas_original"] == 28
    assert result["tripa"]["paginas_final"] == 28
    assert result["tripa"]["pliegos"][0]["frente"] == [30, 3, 28, 5]
    assert result["tripa"]["pliegos"][0]["dorso"] == [4, 29, 6, 27]
    assert result["tripa"]["pliegos"][0]["modo"] == "normal_4_por_cara"
    assert result["tripa"]["pliegos"][0]["paginas_por_cara"] == 4
    assert result["tripa"]["pliegos"][-1] == {
        "pliego": 4,
        "modo": "vyv_2_por_cara",
        "paginas_por_cara": 2,
        "frente": [18, 15],
        "dorso": [16, 17],
    }
    assert result["pliegos"] == result["tripa"]["pliegos"]


def test_simular_cuadernillo_24_paginas_tapa_completa():
    result = simular_cuadernillo(_payload(24, tipo_tapa="tapa_completa"))

    assert result["tapa"]["frente"] == [24, 1]
    assert result["tapa"]["dorso"] == [2, 23]
    assert result["tripa"]["paginas_inicio"] == 3
    assert result["tripa"]["paginas_fin"] == 22
    assert result["tripa"]["paginas_original"] == 20
    assert result["tripa"]["pliegos"][0]["frente"] == [22, 3, 20, 5]
    assert result["tripa"]["pliegos"][-1] == {
        "pliego": 3,
        "modo": "vyv_2_por_cara",
        "paginas_por_cara": 2,
        "frente": [14, 11],
        "dorso": [12, 13],
    }


def test_simular_cuadernillo_30_paginas_tapa_completa_normaliza_a_32():
    result = simular_cuadernillo(_payload(30, tipo_tapa="tapa_completa"))

    assert result["total_paginas_original"] == 30
    assert result["total_paginas_final"] == 32
    assert result["blancas_agregadas"] == 2
    assert result["tapa"]["frente"] == [32, 1]
    assert result["tapa"]["dorso"] == [2, 31]


def test_simular_cuadernillo_pliegos_normales_y_parcial_declaran_paginas_por_cara():
    result = simular_cuadernillo(_payload(32, tipo_tapa="tapa_completa"))
    normales = result["tripa"]["pliegos"][:-1]
    parcial = result["tripa"]["pliegos"][-1]

    assert all(pliego["modo"] == "normal_4_por_cara" for pliego in normales)
    assert all(pliego["paginas_por_cara"] == 4 for pliego in normales)
    assert parcial["modo"] == "vyv_2_por_cara"
    assert parcial["paginas_por_cara"] == 2
    assert len(parcial["frente"]) == 2
    assert len(parcial["dorso"]) == 2


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
