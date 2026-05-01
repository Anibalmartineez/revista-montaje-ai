# 13 SIMULADOR CUADERNILLOS

## Objetivo

La Fase 6.1 agrega un simulador de armado de cuadernillos dentro del Editor Visual IA. Su objetivo es mostrar la distribucion logica de paginas por pliego, frente y dorso, antes de integrar esta informacion con PDF o con el motor de montaje offset.

## Alcance de Fase 6.1

- Modulo aislado: `cuadernillos/simulator.py`.
- Funcion principal: `simular_cuadernillo(payload)`.
- Ruta Flask: `POST /editor_offset/cuadernillos/simular`.
- Panel integrado en `templates/editor_offset_visual.html`.
- Render visual de cada pliego con frente y dorso.

Esta fase no modifica el motor offset actual, no toca Step & Repeat PRO, no cambia la semantica de slots y no integra PDF.

## Reglas de armado

Por ahora solo se soporta:

- `tipo_encuadernacion = "cosido_caballete"`
- `paginas_por_cara = 4`

El total de paginas debe ser un entero positivo. Si no es multiplo de 4, se agregan paginas blancas hasta cerrar el multiplo de 4 siguiente.

Para cada pliego se usa un desplazamiento de 4 paginas:

```text
Pliego 1
frente: [N, 1, N-2, 3]
dorso:  [2, N-1, 4, N-3]

Pliego 2
frente: [N-4, 5, N-6, 7]
dorso:  [6, N-5, 8, N-7]
```

Y asi sucesivamente.

## Estructura JSON

Entrada:

```json
{
  "total_paginas": 32,
  "tipo_encuadernacion": "cosido_caballete",
  "paginas_por_cara": 4,
  "tipo_tapa": "sin_tapa"
}
```

Salida:

```json
{
  "total_paginas_original": 30,
  "total_paginas_final": 32,
  "blancas_agregadas": 2,
  "paginas_por_cara": 4,
  "tipo_encuadernacion": "cosido_caballete",
  "tipo_tapa": "sin_tapa",
  "pliegos": [
    {
      "pliego": 1,
      "frente": [32, 1, 30, 3],
      "dorso": [2, 31, 4, 29]
    }
  ]
}
```

La ruta Flask envuelve la simulacion exitosa como:

```json
{
  "ok": true,
  "simulacion": {}
}
```

Si el modo no esta soportado, devuelve `ok: false` con un mensaje claro.

## Fase 6.2: tapa completa separada

La Fase 6.2 agrega `tipo_tapa` al simulador, manteniendo compatibilidad con la Fase 6.1.

Valores soportados:

- `sin_tapa`: conserva la logica original. Todas las paginas se arman juntas como cuadernillo.
- `tapa_completa`: separa una tapa completa y arma la tripa de manera independiente.

No se implementa todavia `tapa_simple`.

### Regla de tapa completa

Para `total_paginas = N`, primero se normaliza a multiplo de 4 si hace falta. La tapa usa el total final:

```text
TAPA
frente: [N, 1]
dorso:  [2, N-1]
```

La tripa empieza en pagina `3` y termina en pagina `N-2`. Esa lista se arma aparte con la misma regla de cosido a caballete, 4 paginas por cara.

Ejemplo con `N = 32`:

```text
TAPA
frente: [32, 1]
dorso:  [2, 31]

TRIPA
paginas 3 a 30

Pliego 1
frente: [30, 3, 28, 5]
dorso:  [4, 29, 6, 27]
```

Si la tripa no cierra multiplo de 4, el simulador completa el final logico con `"BLANCO"`.

### JSON con tapa completa

```json
{
  "total_paginas_original": 32,
  "total_paginas_final": 32,
  "tipo_encuadernacion": "cosido_caballete",
  "paginas_por_cara": 4,
  "tipo_tapa": "tapa_completa",
  "blancas_agregadas": 0,
  "tapa": {
    "tipo": "tapa_completa",
    "paginas": [32, 1, 2, 31],
    "frente": [32, 1],
    "dorso": [2, 31]
  },
  "tripa": {
    "paginas_inicio": 3,
    "paginas_fin": 30,
    "paginas_original": 28,
    "paginas_final": 28,
    "blancas_agregadas": 0,
    "pliegos": [
      {
        "pliego": 1,
        "frente": [30, 3, 28, 5],
        "dorso": [4, 29, 6, 27]
      }
    ]
  },
  "pliegos": [
    {
      "pliego": 1,
      "frente": [30, 3, 28, 5],
      "dorso": [4, 29, 6, 27]
    }
  ]
}
```

En `tapa_completa`, `pliegos` en la raiz apunta a los pliegos de la tripa para compatibilidad. La UI debe preferir `tapa` y `tripa`.

## Limitaciones actuales

- Solo existe cosido a caballete.
- Solo existe 4 paginas por cara.
- Solo existen `sin_tapa` y `tapa_completa`.
- No hay `tapa_simple`.
- No hay modo vuelta y vuelta.
- No hay integracion PDF.
- No genera ni modifica slots del Editor Visual IA.
- No persiste datos dentro de `layout_constructor.json`.

## Proximos pasos

- Tapa simple.
- Soporte para 2 y 8 paginas por cara.
- Modo vuelta y vuelta.
- Integracion PDF en una fase posterior.
