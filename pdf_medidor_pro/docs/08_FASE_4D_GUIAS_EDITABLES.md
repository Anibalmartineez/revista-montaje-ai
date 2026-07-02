# Fase 4D - Guias editables

## Objetivo

Las guias dejan de ser solo lineas visuales y pasan a comportarse como objetos de trabajo seleccionables dentro del visor de PDF Medidor Pro.

## Crear guias

- Activar la herramienta `Guias`.
- Hacer clic en el visor para crear una guia vertical.
- Mantener `Shift` y hacer clic para crear una guia horizontal.
- Los botones `Guia V` y `Guia H` siguen creando guias centradas.

## Seleccionar y mover

- En modo `Seleccionar`, hacer clic cerca de una guia visible para seleccionarla.
- En modo `Guias`, hacer clic sobre una guia existente la selecciona en vez de crear una nueva.
- Arrastrar una guia seleccionada mueve su posicion:
  - guia vertical: cambia X;
  - guia horizontal: cambia Y.
- La seleccion respeta zoom, pan virtual y conversiones mm/viewport.

## Nudging y borrado

- `Delete` o `Backspace` elimina la guia seleccionada.
- Flechas mueven una guia seleccionada:
  - `0.1 mm` por defecto;
  - `Shift + flecha`: `1 mm`;
  - `Ctrl + flecha`: `0.01 mm`.
- Una guia vertical responde a izquierda/derecha.
- Una guia horizontal responde a arriba/abajo.

## Snap y exportacion

El snap a guias se mantiene activo cuando el toggle `Snap` esta encendido. Las guias visibles tambien siguen incluyendose en el PNG si la opcion de exportar guias esta activa.

El JSON tecnico exportado no cambia. Las guias son estado interno de trabajo y se conservan en el guardado local del navegador.

## Limitaciones actuales

- No hay seleccion multiple de guias.
- No existe bloqueo editable desde la UI; el inspector solo informa si una guia esta bloqueada.
- Las guias no aparecen como filas en el historial inferior.
