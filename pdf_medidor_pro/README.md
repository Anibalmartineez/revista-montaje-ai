# PDF Medidor Pro

PDF Medidor Pro es un modulo aislado para revisar medidas tecnicas de un PDF, renderizar una vista previa y registrar mediciones manuales cuando las cajas automaticas no son suficientes.

## Para que sirve

- Subir un PDF sin tocar el Editor Offset Visual ni Sistema Presupuesto.
- Leer medidas automaticas de `MediaBox`, `CropBox`, `TrimBox`, `BleedBox` y `ArtBox`.
- Renderizar la primera pagina como PNG.
- Medir manualmente lineas y un rectangulo final sobre el preview.
- Calibrar la escala con una medida conocida.
- Exportar un JSON tecnico para futuras integraciones.

## Estructura creada

- `api.py`: blueprint Flask aislado.
- `dev_app.py`: app de desarrollo independiente.
- `config.py`: rutas internas y DPI default.
- `services/`: analisis PDF, render, geometria, medicion, calibracion y export JSON.
- `templates/pdf_medidor_pro.html`: pantalla principal.
- `static/css/pdf_medidor_pro.css`: estilos aislados con prefijo `pmp-`.
- `static/js/`: visor, medicion, rectangulo, calibracion, export y entrypoint.
- `uploads/`, `previews/`, `exports/`: carpetas runtime conservadas con `.gitkeep`.
- `docs/`: arquitectura, API y formato JSON.

## Integracion al sistema principal

El patron detectado en el repositorio es registrar modulos aislados desde `app.py`, como ocurre con `sistema_presupuesto`. Por eso este modulo expone `pdf_medidor_pro_bp` y la app principal solo debe importarlo y registrarlo.

Rutas principales:

- UI: `/pdf-medidor-pro`
- API health: `/api/pdf-medidor-pro/health`
- Upload: `/api/pdf-medidor-pro/upload`
- Export: `/api/pdf-medidor-pro/export`

## Uso manual

1. Ejecutar la app principal:

```bash
python app.py
```

2. Abrir:

```text
http://127.0.0.1:5000/pdf-medidor-pro
```

3. Subir un PDF, revisar medidas automaticas, medir lineas o rectangulo, calibrar si hace falta y exportar JSON.

Para correr solo el modulo:

```bash
python -m pdf_medidor_pro.dev_app
```

Luego abrir:

```text
http://127.0.0.1:5058/pdf-medidor-pro
```
