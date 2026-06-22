# PDF Comercial de Presupuesto

Fase 9.4 agrega generacion de documento comercial para presupuestos guardados.

El modulo sigue aislado: no registra Blueprint en la app principal, no integra con Editor Offset Visual y no toca `routes.py`.

## Formato generado

Formato preferido:

- PDF real usando `reportlab` cuando esta disponible.

Fallback:

- HTML imprimible si `reportlab` no esta disponible en el entorno.

El endpoint informa el tipo generado con:

```text
tipo_documento: "pdf" | "html"
```

## Ubicacion

Los documentos se guardan bajo:

```text
data/pdfs/
```

Archivos generados:

```text
data/pdfs/*.pdf
data/pdfs/*.html
```

La carpeta se conserva con:

```text
data/pdfs/.gitkeep
```

## Contenido minimo

El documento incluye:

- numero comercial si existe;
- `presupuesto_id` tecnico;
- fecha;
- cliente si existe en el presupuesto o puede resolverse por `cliente_id` futuro;
- producto;
- cantidad;
- material;
- maquina;
- colores frente/dorso;
- pliegos buenos;
- pliegos brutos;
- unidades por pliego;
- chapas;
- pasadas;
- subtotal tecnico;
- margen o markup aplicado;
- impuesto;
- precio final;
- precio unitario;
- observaciones;
- nota de validez/configuracion.

## Reglas

- El documento se genera desde un presupuesto guardado por backend.
- No se confia en totales enviados por frontend.
- No se recalcula el presupuesto para emitir el documento.
- Presupuestos antiguos sin `numero_comercial` usan `presupuesto_id` como referencia visible.
- Los nombres de archivo se sanitizan.
- La descarga solo permite archivos dentro de `data/pdfs/`.

## API aislada

Generar documento:

```text
POST /api/sistema-presupuesto/presupuestos/<presupuesto_id>/documento
```

Respuesta:

```json
{
  "ok": true,
  "presupuesto_id": "psp_...",
  "numero_comercial": "PRES-2026-000001",
  "tipo_documento": "pdf",
  "archivo": "PRES-2026-000001.pdf",
  "ruta_relativa": "pdfs/PRES-2026-000001.pdf",
  "mensaje": "Documento PDF comercial generado."
}
```

Descargar o abrir documento:

```text
GET /api/sistema-presupuesto/documentos/<archivo>
```

## UI aislada

La UI permite:

- abrir un presupuesto guardado;
- generar documento comercial;
- ver tipo generado y nombre de archivo;
- abrir el documento generado desde el enlace seguro.

## Limitaciones

- No hay plantillas comerciales editables.
- No hay marca grafica configurable.
- No hay historial avanzado de documentos emitidos.
- No hay asociacion formal cliente-presupuesto todavia.
- No hay integracion con app principal.
- No hay integracion con Editor Offset Visual.
