# Fase 32F — Materialización transformada V2

## Objetivo

Hacer que una página derivada conserve la apariencia del canvas cuando el
operador aplica una transformación gráfica al contenido.

## Comportamiento

- La API acepta la transformación V2 completa y valida valores finitos,
  escalas positivas, rotaciones cardinales, espejos y clipping explícito.
- El servicio prepara la fuente y hornea ajuste, escala, offset, rotación,
  espejo y clipping en una página PDF derivada rasterizada a 300 DPI.
- El tamaño físico de la página derivada es el trim o footprint productivo
  solicitado por el clipping.
- El manifiesto registra la transformación horneada, la caja, el sangrado y
  los hashes de fuente y resultado.
- Al vincular el derivado, el comando revierte el `content_transform` del slot
  a identidad en la misma operación. Deshacer restaura fuente y transformación.
- Preview y PDF final consumen la página derivada una sola vez, evitando aplicar
  la matriz dos veces.

## Seguridad y límites

- El PDF fuente sigue inmutable y cada derivado se publica atómicamente.
- Se mantienen separados los gates de derivados, Preview y PDF final.
- El materializador no añade marcas ni CTP.
- La salida rasterizada requiere comparar fixtures visuales contra Preview; la
  habilitación productiva sigue pendiente de ese gate.

## Pruebas

- fixture de transformación con escala, offset, rotación y espejo;
- dimensiones físicas del PDF derivado;
- manifiesto y hashes;
- vinculación reversible que restablece identidad y deshacer que recupera el
  ajuste original.
