# 02 - API PDF Medidor Pro

## UI

### `GET /pdf-medidor-pro`

Devuelve la pantalla principal del modulo.

### `GET /pdf-medidor-pro/static/<filename>`

Sirve CSS y JS internos.

### `GET /pdf-medidor-pro/previews/<filename>`

Sirve previews PNG renderizados desde PDFs subidos.

## API

### `GET /api/pdf-medidor-pro/health`

Respuesta:

```json
{
  "ok": true,
  "service": "pdf_medidor_pro",
  "status": "ready"
}
```

### `POST /api/pdf-medidor-pro/upload`

Recibe `multipart/form-data` con campo `pdf`.

Validaciones fase 1:

- El archivo debe existir.
- La extension debe ser `.pdf`.
- El nombre se sanea con `secure_filename`.
- El archivo se guarda con UUID para evitar sobrescritura.

Respuesta exitosa:

```json
{
  "ok": true,
  "upload_id": "uuid",
  "archivo": "trabajo.pdf",
  "stored_filename": "uuid_trabajo.pdf",
  "pagina": 1,
  "page_count": 1,
  "medidas_auto": {},
  "render_mm": {},
  "preview": {
    "filename": "uuid_trabajo.png",
    "width_px": 1240,
    "height_px": 1754,
    "dpi": 150,
    "render_mm": {},
    "url": "/pdf-medidor-pro/previews/uuid_trabajo.png"
  },
  "preview_url": "/pdf-medidor-pro/previews/uuid_trabajo.png"
}
```

### `POST /api/pdf-medidor-pro/render-page`

Renderiza una pagina especifica de un PDF ya subido.

Request:

```json
{
  "stored_filename": "uuid_trabajo.pdf",
  "pagina": 2
}
```

Respuesta exitosa:

```json
{
  "ok": true,
  "pagina": 2,
  "page_count": 4,
  "medidas_auto": {},
  "render_mm": {},
  "preview": {
    "filename": "uuid_trabajo_p2.png",
    "width_px": 1240,
    "height_px": 1754,
    "dpi": 150,
    "render_mm": {},
    "url": "/pdf-medidor-pro/previews/uuid_trabajo_p2.png"
  },
  "preview_url": "/pdf-medidor-pro/previews/uuid_trabajo_p2.png"
}
```

`pagina` usa indice humano desde `1`. Si la pagina no existe, la API devuelve error `PAGE_RENDER_FAILED`.

### `POST /api/pdf-medidor-pro/export`

Recibe el contrato tecnico en JSON. El backend normaliza campos numericos y guarda un `.json` en `exports/`.

Respuesta exitosa:

```json
{
  "ok": true,
  "export": {},
  "filename": "pdf_medidor_pro_uuid.json",
  "url": "/api/pdf-medidor-pro/exports/pdf_medidor_pro_uuid.json"
}
```

### `GET /api/pdf-medidor-pro/exports/<filename>`

Devuelve un JSON exportado.
