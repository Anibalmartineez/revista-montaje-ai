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
- `tipo_cuadernillo = 8` o `16`

El total de paginas debe ser un entero positivo. Si no es multiplo de 4, se agregan paginas blancas hasta cerrar el multiplo de 4 siguiente.

Historicamente, Fase 6.1 usaba un desplazamiento simple de 4 paginas:

```text
Pliego 1
frente: [N, 1, N-2, 3]
dorso:  [2, N-1, 4, N-3]

Pliego 2
frente: [N-4, 5, N-6, 7]
dorso:  [6, N-5, 8, N-7]
```

Desde Fase 6.4 y 6.5, la salida operativa usa patrones reales validados de cuadernillo 8/16 y toma paginas desde extremos.

## Estructura JSON

Entrada:

```json
{
  "total_paginas": 32,
  "tipo_encuadernacion": "cosido_caballete",
  "tipo_tapa": "sin_tapa",
  "tipo_cuadernillo": 8
}
```

`paginas_por_cara` ya no es un input de usuario. Si aparece en un payload viejo, el backend lo ignora y lo deriva automaticamente desde `tipo_cuadernillo`.

Salida:

```json
{
  "total_paginas_original": 30,
  "total_paginas_final": 32,
  "blancas_agregadas": 2,
  "paginas_por_cara": 4,
  "tipo_encuadernacion": "cosido_caballete",
  "tipo_tapa": "sin_tapa",
  "tipo_cuadernillo": 8,
  "pliegos": [
    {
      "pliego": 1,
      "tipo": "cuadernillo_8",
      "modo": "cuadernillo_8",
      "paginas_por_cara": 4,
      "frente": [32, 29, 1, 4],
      "dorso": [30, 31, 3, 2]
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

Ejemplo con `N = 32` y `tipo_cuadernillo = 8`:

```text
TAPA
frente: [32, 1]
dorso:  [2, 31]

TRIPA
paginas 3 a 30

Pliego 1
frente: [30, 27, 3, 6]
dorso:  [28, 29, 5, 4]
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
        "tipo": "cuadernillo_8",
        "modo": "cuadernillo_8",
        "paginas_por_cara": 4,
        "frente": [29, 3, 30, 4],
        "dorso": [5, 28, 6, 27]
      }
    ]
  },
  "pliegos": [
    {
      "pliego": 1,
      "tipo": "cuadernillo_8",
      "modo": "cuadernillo_8",
      "paginas_por_cara": 4,
      "frente": [29, 3, 30, 4],
      "dorso": [5, 28, 6, 27]
    }
  ]
}
```

En `tapa_completa`, `pliegos` en la raiz apunta a los pliegos de la tripa para compatibilidad. La UI debe preferir `tapa` y `tripa`.

## Fase 6.3: pliegos parciales

La Fase 6.3 corrige el armado de tripas cuando queda un bloque final de 4 paginas. Antes, el simulador trataba ese bloque como si fuera un pliego completo de 8 paginas. En imprenta real, ese caso se resuelve como pliego parcial vuelta y vuelta con 2 paginas por cara.

Nota: esta fase quedo superada por Fase 6.4 y Fase 6.5. La implementacion actual usa `vyv_4` y `vyv_8` como cara unica, con patrones validados.

### Pliego completo

Mientras quedan 8 paginas o mas en la tripa, se usa el modo normal:

```json
{
  "pliego": 1,
  "modo": "normal_4_por_cara",
  "paginas_por_cara": 4,
  "frente": [30, 3, 28, 5],
  "dorso": [4, 29, 6, 27]
}
```

Este modo consume 4 paginas del inicio logico de la tripa y 4 paginas del final logico.

### Pliego parcial VYV

Cuando quedan exactamente 4 paginas, se usa automaticamente:

- `modo = "vyv_2_por_cara"`
- `paginas_por_cara = 2`

Para paginas `[a, b, c, d]`, donde `a` es la menor y `d` la mayor:

```text
frente: [d, a]
dorso:  [b, c]
```

Ejemplo:

```json
{
  "pliego": 4,
  "modo": "vyv_2_por_cara",
  "paginas_por_cara": 2,
  "frente": [18, 15],
  "dorso": [16, 17]
}
```

### Ejemplo con tapa completa

Para una revista final de 32 paginas con `tapa_completa`:

- tapa: paginas `[32, 1, 2, 31]`
- tripa: paginas `3` a `30`
- tripa total: 28 paginas

La tripa se arma como:

- pliegos 1 a 3: `normal_4_por_cara`
- pliego 4: `vyv_2_por_cara` con paginas `[15, 16, 17, 18]`

Esto evita mezclar bloques de 4 y 8 paginas dentro del mismo pliego y evita generar un pliego parcial como si fuera completo.

## Fase 6.4: cuadernillos reales y VYV

La Fase 6.4 agrega un motor configurable con `tipo_cuadernillo`:

- `8`: cuadernillos de 8 paginas.
- `16`: cuadernillos de 16 paginas.

`paginas_por_cara` se deriva automaticamente:

- `tipo_cuadernillo = 8` -> `paginas_por_cara = 4`
- `tipo_cuadernillo = 16` -> `paginas_por_cara = 8`

La UI no muestra selector manual para paginas por cara; solo informa que el valor es automatico.

El flujo sigue siendo:

- siempre cosido a caballete
- siempre cabeza con cabeza
- siempre con logica espejo inicio-final
- sin integracion PDF
- sin tocar Step & Repeat PRO

### Tapa

La tapa completa se mantiene igual:

```text
frente: [N, 1]
dorso:  [2, N-1]
```

### Tripa

La tripa se genera como lista:

```text
[3 ... N-2]
```

No se divide en bloques consecutivos. El motor toma paginas desde ambos extremos:

```text
tipo_cuadernillo = 16
tomar 8 del inicio + 8 del final

tipo_cuadernillo = 8
tomar 4 del inicio + 4 del final
```

### Cuadernillo 8

Para 4 paginas tomadas del inicio y 4 del final se arma:

```json
{
  "pliego": 1,
  "tipo": "cuadernillo_8",
  "modo": "cuadernillo_8",
  "paginas_por_cara": 4,
  "frente": [29, 3, 30, 4],
  "dorso": [5, 28, 6, 27]
}
```

### Cuadernillo 16

Para 8 paginas tomadas del inicio y 8 del final se arma en layout 2x4:

```json
{
  "pliego": 1,
  "tipo": "cuadernillo_16",
  "modo": "cuadernillo_16",
  "paginas_por_cara": 8,
  "frente": [34, 3, 32, 5, 30, 7, 28, 9],
  "dorso": [4, 33, 6, 31, 8, 29, 10, 27]
}
```

Ese ejemplo corresponde a una revista de 36 paginas con tapa completa:

- tapa: `[36, 1, 2, 35]`
- tripa: `3..34`
- primer cuadernillo 16: inicio `3..10`, final `27..34`

### VYV automatico

Cuando el motor no alcanza a completar otro cuadernillo:

- si quedan 8 paginas, genera `vyv_8`
- si quedan 4 paginas, genera `vyv_4`

VYV no tiene frente/dorso. Tiene una sola `cara`.

Ejemplo `vyv_8`:

```json
{
  "pliego": 2,
  "tipo": "vyv_8",
  "modo": "vyv_8_paginas",
  "paginas_por_cara": 8,
  "cara": [18, 11, 16, 13, 14, 15, 12, 17]
}
```

Ejemplo `vyv_4`:

```json
{
  "pliego": 2,
  "tipo": "vyv_4",
  "modo": "vyv_4_paginas",
  "paginas_por_cara": 4,
  "cara": [12, 9, 10, 11]
}
```

La UI debe renderizar los cuadernillos con frente/dorso y los VYV como cara unica.

## Fase 6.5: patrones reales validados

La Fase 6.5 congela los patrones de imposicion como constantes auditables en `cuadernillos/simulator.py`.

### Patron de 8 paginas

Para paginas logicas `[1,2,3,4,5,6,7,8]`:

```text
frente:
[8, 5]
[1, 4]

dorso:
[6, 7]
[3, 2]
```

En arrays lineales:

```json
{
  "frente": [8, 5, 1, 4],
  "dorso": [6, 7, 3, 2]
}
```

### Patron de 16 paginas

Para paginas logicas `[1..16]`:

```text
frente:
[5, 12, 9, 8]
[4, 13, 16, 1]

dorso:
[7, 10, 11, 6]
[2, 15, 14, 3]
```

En arrays lineales:

```json
{
  "frente": [5, 12, 9, 8, 4, 13, 16, 1],
  "dorso": [7, 10, 11, 6, 2, 15, 14, 3]
}
```

### Mapeo a paginas reales

Los patrones son relativos a las paginas tomadas por cada cuadernillo.

Ejemplo: una revista de 36 paginas con tapa completa tiene:

- tapa: `[36, 1, 2, 35]`
- tripa: `[3..34]`
- primer cuadernillo 16: `[3,4,5,6,7,8,9,10,27,28,29,30,31,32,33,34]`

El indice logico 1 corresponde a `3`, el indice logico 2 corresponde a `4`, y asi sucesivamente.

Aplicando el patron de 16:

```json
{
  "frente": [7, 30, 27, 10, 6, 31, 34, 3],
  "dorso": [9, 28, 29, 8, 4, 33, 32, 5]
}
```

### VYV como cara unica

VYV no tiene frente/dorso. Se renderiza como `cara` unica.

Patrones VYV auditables:

```text
vyv_4: [4, 1, 2, 3]
vyv_8: [8, 1, 6, 3, 4, 5, 2, 7]
```

Ejemplos:

```json
{
  "tipo": "vyv_4",
  "modo": "vyv_4_paginas",
  "paginas_por_cara": 4,
  "cara": [12, 9, 10, 11]
}
```

```json
{
  "tipo": "vyv_8",
  "modo": "vyv_8_paginas",
  "paginas_por_cara": 8,
  "cara": [18, 11, 16, 13, 14, 15, 12, 17]
}
```

## Limitaciones actuales

- Solo existe cosido a caballete.
- El campo historico `paginas_por_cara` del payload se ignora; la cantidad real por cara se deriva del tipo de cuadernillo y tambien se informa en `pliegos[].paginas_por_cara`.
- Solo existen `sin_tapa` y `tapa_completa`.
- Solo existen cuadernillos configurables de 8 o 16 paginas.
- No hay `tapa_simple`.
- Vuelta y vuelta solo se aplica automaticamente como `vyv_4` o `vyv_8`.
- No hay integracion PDF.
- No genera ni modifica slots del Editor Visual IA.
- No persiste datos dentro de `layout_constructor.json`.

## Proximos pasos

- Tapa simple.
- Nuevos tipos de cuadernillo si produccion los requiere.
- Modo vuelta y vuelta.
- Integracion PDF en una fase posterior.
