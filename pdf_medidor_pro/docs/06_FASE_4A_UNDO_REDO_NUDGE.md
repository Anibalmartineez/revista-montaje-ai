# 06 - Fase 4A Undo/Redo y Fase 4B Nudging

## Objetivo

Esta fase agrega control profesional sobre objetos de medicion sin cambiar rutas, backend ni contrato JSON.

## Undo / Redo

El historial reversible vive en `static/js/undo_redo.js` y conserva hasta 50 estados. Cada estado guarda solo datos de objetos:

- `measurements`;
- `selectedMeasurementId`;
- `finalMeasurementId`;
- `finalOrigin`;
- `finalConfidence`.

Acciones registradas:

- crear linea;
- crear rectangulo;
- eliminar objeto;
- mover objeto;
- redimensionar rectangulo;
- renombrar objeto;
- cambiar color;
- mostrar/ocultar;
- duplicar objeto existente;
- cambiar medida final.

Atajos:

- `Ctrl+Z`: deshacer;
- `Ctrl+Y`: rehacer;
- `Ctrl+Shift+Z`: rehacer.

Los botones `Deshacer` y `Rehacer` se activan o desactivan segun disponibilidad de historial.

## Nudging

El nudging mueve el objeto seleccionado en coordenadas canonicas de pagina, expresadas en milimetros:

- Flechas: `0.1 mm`;
- `Shift + Flechas`: `1 mm`;
- `Ctrl + Flechas`: `0.01 mm`.

Funciona con lineas y rectangulos. No actua cuando no hay seleccion, cuando el usuario escribe en un campo o cuando hay un dialogo modal abierto.

## No alcance

- No agrega capas.
- No agrega seleccion multiple.
- No agrega copiar/pegar.
- No cambia export JSON.
- No agrega persistencia backend.
- No modifica snap para teclado: el nudging mantiene incrementos exactos.
