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
  "paginas_por_cara": 4
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

## Limitaciones actuales

- Solo existe cosido a caballete.
- Solo existe 4 paginas por cara.
- No hay tratamiento especial de tapa.
- No hay modo vuelta y vuelta.
- No hay integracion PDF.
- No genera ni modifica slots del Editor Visual IA.
- No persiste datos dentro de `layout_constructor.json`.

## Proximos pasos

- Tapa separada.
- Soporte para 2 y 8 paginas por cara.
- Modo vuelta y vuelta.
- Integracion PDF en una fase posterior.
