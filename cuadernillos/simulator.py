import math


TIPO_SOPORTADO = "cosido_caballete"
PAGINAS_POR_CARA_SOPORTADAS = 4


class CuadernilloSimulationError(ValueError):
    pass


def _validar_total_paginas(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise CuadernilloSimulationError("total_paginas debe ser un entero positivo.")
    if value <= 0:
        raise CuadernilloSimulationError("total_paginas debe ser un entero positivo.")
    return value


def _normalizar_total(total_paginas):
    return int(math.ceil(total_paginas / 4) * 4)


def simular_cuadernillo(payload):
    if not isinstance(payload, dict):
        raise CuadernilloSimulationError("El payload debe ser un objeto JSON.")

    tipo_encuadernacion = payload.get("tipo_encuadernacion")
    paginas_por_cara = payload.get("paginas_por_cara")

    if tipo_encuadernacion != TIPO_SOPORTADO:
        raise CuadernilloSimulationError(
            "Modo no soportado. Por ahora solo se soporta cosido_caballete."
        )
    if paginas_por_cara != PAGINAS_POR_CARA_SOPORTADAS:
        raise CuadernilloSimulationError(
            "Modo no soportado. Por ahora solo se soportan 4 paginas por cara."
        )

    total_original = _validar_total_paginas(payload.get("total_paginas"))
    total_final = _normalizar_total(total_original)
    blancas_agregadas = total_final - total_original

    pliegos = []
    for offset in range(0, total_final // 2, 4):
        pliegos.append(
            {
                "pliego": len(pliegos) + 1,
                "frente": [
                    total_final - offset,
                    1 + offset,
                    total_final - offset - 2,
                    3 + offset,
                ],
                "dorso": [
                    2 + offset,
                    total_final - offset - 1,
                    4 + offset,
                    total_final - offset - 3,
                ],
            }
        )

    return {
        "total_paginas_original": total_original,
        "total_paginas_final": total_final,
        "blancas_agregadas": blancas_agregadas,
        "paginas_por_cara": paginas_por_cara,
        "tipo_encuadernacion": tipo_encuadernacion,
        "pliegos": pliegos,
    }

