# 04 - Fase 2 Zoom, Lupa y Snap

## Resumen

Fase 2 concentra el modulo en medicion tecnica precisa para preprensa:

- zoom profesional;
- pan;
- lupa de precision;
- snap;
- medicion por linea;
- rectangulo final;
- calibracion;
- export JSON compatible.

No hay medicion inteligente ni comandos automatizados en esta fase.

## Coordenadas canonicas

Las mediciones viven en milimetros de pagina:

- Linea: `a.x_mm`, `a.y_mm`, `b.x_mm`, `b.y_mm`.
- Rectangulo: `x_mm`, `y_mm`, `ancho_mm`, `alto_mm`.

El visor convierte esas coordenadas a pixeles solo para dibujar. Esto permite zoom, pan, lupa y snap sin desplazar mediciones.

## Zoom y pan

- Presets: 25%, 50%, 100%, 200%, 400%, 800%, 1600%, 3200%.
- `1:1` representa el PNG renderizado en escala nativa.
- Rueda del mouse hace zoom anclado al cursor.
- La herramienta mano y la barra espaciadora permiten pan.

## Lupa

La lupa usa el mismo preview y respeta zoom/pan. Puede activarse desde el boton o temporalmente con `Alt`.

Factores:

- 5x
- 10x
- 20x

## Snap

El snap es opcional. Ajusta puntos a:

- extremos de lineas;
- esquinas de rectangulos;
- centros;
- puntos medios de bordes.

Mantener `Ctrl` usa umbral estricto.

## Export

El contrato base se mantiene. La clave `mediciones` puede conservar historial de lineas y rectangulos manuales, sin depender de automatizaciones externas.
