# Fase 4E - Soporte multipagina real

## Objetivo

PDF Medidor Pro soporta PDFs con mas de una pagina sin mezclar mediciones entre paginas.

## Navegacion

- El upload conserva `stored_filename` y `page_count`.
- La barra superior permite ir a pagina anterior, siguiente o escribir una pagina.
- Cada pagina se renderiza bajo demanda mediante `/api/pdf-medidor-pro/render-page`.
- La pagina 1 sigue cargando desde `/api/pdf-medidor-pro/upload`.

## Estado por pagina

El frontend mantiene una vista activa para conservar las herramientas existentes, pero guarda cada pagina en `state.pages`.

Cada pagina conserva:

- mediciones;
- guias;
- seleccion activa;
- rectangulo final;
- origen/confianza de medida final;
- medidas automaticas;
- datos de render y preview.

La calibracion permanece global para el documento.

## Exportacion

El JSON conserva el contrato base para la pagina activa y agrega:

- `page_count`;
- `paginas[]` con mediciones agrupadas por pagina;
- `mediciones` como lista plana de todas las paginas.

Las guias no se exportan en JSON. El PNG exportado corresponde solo a la pagina actual.

## Compatibilidad

Los PDFs de una sola pagina siguen usando el flujo anterior: upload, preview de pagina 1, mediciones y export JSON base. La ampliacion multipagina agrega campos compatibles sin quitar claves existentes.

## Limitaciones actuales

- Las paginas no visitadas aparecen en `paginas[]` sin mediciones y con cajas automaticas vacias hasta que se rendericen.
- Undo/redo opera sobre la pagina activa; al cambiar de pagina se reinicia el historial reversible.
- El guardado local conserva datos editables por documento, pero los previews se regeneran desde el PDF subido.
