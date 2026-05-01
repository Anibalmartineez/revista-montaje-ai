import math


TIPO_SOPORTADO = "cosido_caballete"
PAGINAS_POR_CARA_SOPORTADAS = 4
TIPOS_TAPA_SOPORTADOS = {"sin_tapa", "tapa_completa"}
PAGINA_BLANCA = "BLANCO"


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


def _normalizar_paginas_tripa(paginas):
    paginas_normalizadas = list(paginas)
    resto = len(paginas_normalizadas) % 4
    blancas = 0 if resto == 0 else 4 - resto
    paginas_normalizadas.extend([PAGINA_BLANCA] * blancas)
    return paginas_normalizadas, blancas


def _armar_pliegos_desde_paginas(paginas):
    paginas_finales, _ = _normalizar_paginas_tripa(paginas)
    pliegos = []
    total = len(paginas_finales)
    offset = 0

    while total - (offset * 2) >= 8:
        pliegos.append(
            {
                "pliego": len(pliegos) + 1,
                "modo": "normal_4_por_cara",
                "paginas_por_cara": 4,
                "frente": [
                    paginas_finales[total - 1 - offset],
                    paginas_finales[offset],
                    paginas_finales[total - 3 - offset],
                    paginas_finales[offset + 2],
                ],
                "dorso": [
                    paginas_finales[offset + 1],
                    paginas_finales[total - 2 - offset],
                    paginas_finales[offset + 3],
                    paginas_finales[total - 4 - offset],
                ],
            }
        )
        offset += 4

    if total - (offset * 2) == 4:
        paginas_parciales = paginas_finales[offset : offset + 4]
        pliegos.append(
            {
                "pliego": len(pliegos) + 1,
                "modo": "vyv_2_por_cara",
                "paginas_por_cara": 2,
                "frente": [paginas_parciales[3], paginas_parciales[0]],
                "dorso": [paginas_parciales[1], paginas_parciales[2]],
            }
        )

    return pliegos


def _validar_modo(payload):
    if not isinstance(payload, dict):
        raise CuadernilloSimulationError("El payload debe ser un objeto JSON.")

    tipo_encuadernacion = payload.get("tipo_encuadernacion")
    paginas_por_cara = payload.get("paginas_por_cara")
    tipo_tapa = payload.get("tipo_tapa", "sin_tapa")

    if tipo_encuadernacion != TIPO_SOPORTADO:
        raise CuadernilloSimulationError(
            "Modo no soportado. Por ahora solo se soporta cosido_caballete."
        )
    if paginas_por_cara != PAGINAS_POR_CARA_SOPORTADAS:
        raise CuadernilloSimulationError(
            "Modo no soportado. Por ahora solo se soportan 4 paginas por cara."
        )
    if tipo_tapa not in TIPOS_TAPA_SOPORTADOS:
        raise CuadernilloSimulationError(
            "Tipo de tapa no soportado. Por ahora solo se soporta sin_tapa o tapa_completa."
        )

    total_original = _validar_total_paginas(payload.get("total_paginas"))
    if tipo_tapa == "tapa_completa" and total_original < 8:
        raise CuadernilloSimulationError(
            "Para tapa_completa, total_paginas debe ser al menos 8."
        )

    return total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa


def _simular_sin_tapa(total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa):
    total_final = _normalizar_total(total_original)
    blancas_agregadas = total_final - total_original
    pliegos = _armar_pliegos_desde_paginas(range(1, total_final + 1))

    return {
        "total_paginas_original": total_original,
        "total_paginas_final": total_final,
        "blancas_agregadas": blancas_agregadas,
        "paginas_por_cara": paginas_por_cara,
        "tipo_encuadernacion": tipo_encuadernacion,
        "tipo_tapa": tipo_tapa,
        "pliegos": pliegos,
    }


def _simular_tapa_completa(total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa):
    total_final = _normalizar_total(total_original)
    blancas_total = total_final - total_original
    paginas_tripa_originales = list(range(3, total_final - 1))
    paginas_tripa_finales, blancas_tripa = _normalizar_paginas_tripa(paginas_tripa_originales)
    pliegos_tripa = _armar_pliegos_desde_paginas(paginas_tripa_originales)
    tapa = {
        "tipo": tipo_tapa,
        "paginas": [total_final, 1, 2, total_final - 1],
        "frente": [total_final, 1],
        "dorso": [2, total_final - 1],
    }
    tripa = {
        "paginas_inicio": 3,
        "paginas_fin": total_final - 2,
        "paginas_original": len(paginas_tripa_originales),
        "paginas_final": len(paginas_tripa_finales),
        "blancas_agregadas": blancas_tripa,
        "pliegos": pliegos_tripa,
    }

    return {
        "total_paginas_original": total_original,
        "total_paginas_final": total_final,
        "tipo_encuadernacion": tipo_encuadernacion,
        "paginas_por_cara": paginas_por_cara,
        "tipo_tapa": tipo_tapa,
        "blancas_agregadas": blancas_total,
        "tapa": tapa,
        "tripa": tripa,
        "pliegos": pliegos_tripa,
    }


def simular_cuadernillo(payload):
    total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa = _validar_modo(payload)
    if tipo_tapa == "tapa_completa":
        return _simular_tapa_completa(
            total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa
        )
    return _simular_sin_tapa(total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa)
