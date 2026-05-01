import math


TIPO_SOPORTADO = "cosido_caballete"
TIPOS_TAPA_SOPORTADOS = {"sin_tapa", "tapa_completa"}
TIPOS_CUADERNILLO_SOPORTADOS = {8, 16}
PAGINA_BLANCA = "BLANCO"
PATRON_8_FRENTE = (8, 5, 1, 4)
PATRON_8_DORSO = (6, 7, 3, 2)
PATRON_16_FRENTE = (5, 12, 9, 8, 4, 13, 16, 1)
PATRON_16_DORSO = (7, 10, 11, 6, 2, 15, 14, 3)
PATRON_VYV_4_CARA = (4, 1, 2, 3)
PATRON_VYV_8_CARA = (8, 1, 6, 3, 4, 5, 2, 7)


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


def _validar_tipo_cuadernillo(value):
    if value is None:
        return 8
    if isinstance(value, bool) or not isinstance(value, int):
        raise CuadernilloSimulationError("tipo_cuadernillo debe ser 8 o 16.")
    if value not in TIPOS_CUADERNILLO_SOPORTADOS:
        raise CuadernilloSimulationError("tipo_cuadernillo debe ser 8 o 16.")
    return value


def _mapear_patron(paginas, patron):
    return [paginas[idx - 1] for idx in patron]


def _paginas_visual(paginas):
    mitad = len(paginas) // 2
    return [
        {"pagina": pagina, "rotacion": 180 if idx < mitad else 0}
        for idx, pagina in enumerate(paginas)
    ]


def _cuadernillo_8(pliego_num, paginas):
    frente = _mapear_patron(paginas, PATRON_8_FRENTE)
    dorso = _mapear_patron(paginas, PATRON_8_DORSO)
    return {
        "pliego": pliego_num,
        "tipo": "cuadernillo_8",
        "modo": "cuadernillo_8",
        "paginas_por_cara": 4,
        "frente": frente,
        "dorso": dorso,
        "frente_visual": _paginas_visual(frente),
        "dorso_visual": _paginas_visual(dorso),
    }


def _cuadernillo_16(pliego_num, paginas):
    frente = _mapear_patron(paginas, PATRON_16_FRENTE)
    dorso = _mapear_patron(paginas, PATRON_16_DORSO)
    return {
        "pliego": pliego_num,
        "tipo": "cuadernillo_16",
        "modo": "cuadernillo_16",
        "paginas_por_cara": 8,
        "frente": frente,
        "dorso": dorso,
        "frente_visual": _paginas_visual(frente),
        "dorso_visual": _paginas_visual(dorso),
    }


def _vyv_4(pliego_num, pages):
    cara = _mapear_patron(pages, PATRON_VYV_4_CARA)
    return {
        "pliego": pliego_num,
        "tipo": "vyv_4",
        "modo": "vyv_4_paginas",
        "paginas_por_cara": 4,
        "cara": cara,
        "cara_visual": _paginas_visual(cara),
    }


def _vyv_8(pliego_num, pages):
    cara = _mapear_patron(pages, PATRON_VYV_8_CARA)
    return {
        "pliego": pliego_num,
        "tipo": "vyv_8",
        "modo": "vyv_8_paginas",
        "paginas_por_cara": 8,
        "cara": cara,
        "cara_visual": _paginas_visual(cara),
    }


def _armar_pliegos_desde_paginas(paginas, tipo_cuadernillo=8):
    paginas_finales, _ = _normalizar_paginas_tripa(paginas)
    pliegos = []
    inicio = 0
    fin = len(paginas_finales)

    while fin - inicio > 0:
        restantes = fin - inicio
        pliego_num = len(pliegos) + 1

        if tipo_cuadernillo == 16 and restantes >= 16:
            start_pages = paginas_finales[inicio : inicio + 8]
            end_pages = paginas_finales[fin - 8 : fin]
            pliegos.append(_cuadernillo_16(pliego_num, start_pages + end_pages))
            inicio += 8
            fin -= 8
            continue

        if tipo_cuadernillo == 8 and restantes >= 8:
            start_pages = paginas_finales[inicio : inicio + 4]
            end_pages = paginas_finales[fin - 4 : fin]
            pliegos.append(_cuadernillo_8(pliego_num, start_pages + end_pages))
            inicio += 4
            fin -= 4
            continue

        if tipo_cuadernillo == 16 and restantes == 12:
            start_pages = paginas_finales[inicio : inicio + 4]
            end_pages = paginas_finales[fin - 4 : fin]
            pliegos.append(_cuadernillo_8(pliego_num, start_pages + end_pages))
            inicio += 4
            fin -= 4
            continue

        paginas_restantes = paginas_finales[inicio:fin]
        if restantes == 8:
            pliegos.append(_vyv_8(pliego_num, paginas_restantes))
            break
        if restantes == 4:
            pliegos.append(_vyv_4(pliego_num, paginas_restantes))
            break

        raise CuadernilloSimulationError(
            "No se pudo cerrar la tripa en cuadernillos completos o VYV."
        )

    return pliegos


def _validar_modo(payload):
    if not isinstance(payload, dict):
        raise CuadernilloSimulationError("El payload debe ser un objeto JSON.")

    tipo_encuadernacion = payload.get("tipo_encuadernacion")
    tipo_tapa = payload.get("tipo_tapa", "sin_tapa")
    tipo_cuadernillo = _validar_tipo_cuadernillo(payload.get("tipo_cuadernillo"))
    paginas_por_cara = 4 if tipo_cuadernillo == 8 else 8

    if tipo_encuadernacion != TIPO_SOPORTADO:
        raise CuadernilloSimulationError(
            "Modo no soportado. Por ahora solo se soporta cosido_caballete."
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

    return (
        total_original,
        tipo_encuadernacion,
        paginas_por_cara,
        tipo_tapa,
        tipo_cuadernillo,
    )


def _simular_sin_tapa(
    total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa, tipo_cuadernillo
):
    total_final = _normalizar_total(total_original)
    blancas_agregadas = total_final - total_original
    pliegos = _armar_pliegos_desde_paginas(range(1, total_final + 1), tipo_cuadernillo)

    return {
        "total_paginas_original": total_original,
        "total_paginas_final": total_final,
        "blancas_agregadas": blancas_agregadas,
        "paginas_por_cara": paginas_por_cara,
        "tipo_encuadernacion": tipo_encuadernacion,
        "tipo_tapa": tipo_tapa,
        "tipo_cuadernillo": tipo_cuadernillo,
        "pliegos": pliegos,
    }


def _simular_tapa_completa(
    total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa, tipo_cuadernillo
):
    total_final = _normalizar_total(total_original)
    blancas_total = total_final - total_original
    paginas_tripa_originales = list(range(3, total_final - 1))
    paginas_tripa_finales, blancas_tripa = _normalizar_paginas_tripa(paginas_tripa_originales)
    pliegos_tripa = _armar_pliegos_desde_paginas(paginas_tripa_originales, tipo_cuadernillo)
    tapa = {
        "tipo": tipo_tapa,
        "paginas": [total_final, 1, 2, total_final - 1],
        "frente": [total_final, 1],
        "dorso": [2, total_final - 1],
        "frente_visual": [
            {"pagina": total_final, "rotacion": 0},
            {"pagina": 1, "rotacion": 0},
        ],
        "dorso_visual": [
            {"pagina": 2, "rotacion": 0},
            {"pagina": total_final - 1, "rotacion": 0},
        ],
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
        "tipo_cuadernillo": tipo_cuadernillo,
        "blancas_agregadas": blancas_total,
        "tapa": tapa,
        "tripa": tripa,
        "pliegos": pliegos_tripa,
    }


def simular_cuadernillo(payload):
    (
        total_original,
        tipo_encuadernacion,
        paginas_por_cara,
        tipo_tapa,
        tipo_cuadernillo,
    ) = _validar_modo(payload)
    if tipo_tapa == "tapa_completa":
        return _simular_tapa_completa(
            total_original,
            tipo_encuadernacion,
            paginas_por_cara,
            tipo_tapa,
            tipo_cuadernillo,
        )
    return _simular_sin_tapa(
        total_original, tipo_encuadernacion, paginas_por_cara, tipo_tapa, tipo_cuadernillo
    )
