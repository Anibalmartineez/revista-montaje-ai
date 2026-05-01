from pathlib import Path
import os
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OPENAI_API_KEY", "test")

import pytest

from app import app
from cuadernillos.simulator import CuadernilloSimulationError, simular_cuadernillo


def _payload(total_paginas, tipo="cosido_caballete", paginas_por_cara=4):
    return {
        "total_paginas": total_paginas,
        "tipo_encuadernacion": tipo,
        "paginas_por_cara": paginas_por_cara,
    }


def test_simular_cuadernillo_16_paginas():
    result = simular_cuadernillo(_payload(16))

    assert result["total_paginas_original"] == 16
    assert result["total_paginas_final"] == 16
    assert result["blancas_agregadas"] == 0
    assert result["pliegos"] == [
        {"pliego": 1, "frente": [16, 1, 14, 3], "dorso": [2, 15, 4, 13]},
        {"pliego": 2, "frente": [12, 5, 10, 7], "dorso": [6, 11, 8, 9]},
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
        "frente": [32, 1, 30, 3],
        "dorso": [2, 31, 4, 29],
    }


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

