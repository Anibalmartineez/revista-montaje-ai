# PDF Medidor Pro

PDF Medidor Pro es un modulo aislado para revisar medidas tecnicas de un PDF, renderizar una vista previa y registrar mediciones manuales cuando las cajas automaticas no son suficientes.

## Para que sirve

- Subir un PDF sin tocar el Editor Offset Visual ni Sistema Presupuesto.
- Leer medidas automaticas de `MediaBox`, `CropBox`, `TrimBox`, `BleedBox` y `ArtBox`.
- Renderizar la primera pagina como PNG.
- Medir manualmente lineas y rectangulos como objetos editables.
- Calibrar la escala con una medida conocida.
- Hacer zoom profesional, pan, lupa y snap.
- Seleccionar, mover, renombrar, ocultar, duplicar y redimensionar mediciones.
- Deshacer, rehacer y ajustar objetos con flechas en pasos de precision.
- Mantener una interfaz sin duplicacion visual: topbar para acciones, panel izquierdo para herramientas e inspector derecho para informacion tecnica.
- Exportar PNG desde el navegador con preview, mediciones y guias visibles.
- Crear, seleccionar, mover y borrar guias editables para alinear mediciones tecnicas.
- Exportar un JSON tecnico para futuras integraciones.

## Estructura creada

- `api.py`: blueprint Flask aislado.
- `dev_app.py`: app de desarrollo independiente.
- `config.py`: rutas internas y DPI default.
- `services/`: analisis PDF, render, geometria, medicion, calibracion y export JSON.
- `templates/pdf_medidor_pro.html`: pantalla principal.
- `static/css/pdf_medidor_pro.css`: estilos aislados con prefijo `pmp-`.
- `static/js/`: visor, medicion, rectangulo, calibracion, export y entrypoint.
- `static/js/magnifier.js`, `snap.js`: precision visual de Fase 2.
- `static/js/object_model.js`: operaciones puras para objetos editables.
- `static/js/undo_redo.js`: historial reversible de objetos de medicion.
- `static/js/inspector_panel.js`, `history_panel.js`, `guides.js`, `png_export.js`: UI profesional de Fase 3.
- `services/snap_engine.py`: motor de snap de Fase 2.
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

3. Subir un PDF, revisar medidas automaticas, usar zoom/pan/lupa/snap, medir lineas o rectangulos, seleccionar objetos, mover/redimensionar, calibrar si hace falta y exportar JSON o PNG.

## Fase 3

La Fase 3 convierte la pantalla en una herramienta de medicion de preprensa:

- barra superior con apertura, guardado local, export JSON/PNG, zoom y herramientas rapidas;
- panel izquierdo con herramientas, color, grosor, unidad, decimales, snap, guias, lupa y calibracion;
- visor central con reglas, centro de pagina, coordenadas, guias, lupa, snap y objetos editables;
- inspector derecho contextual para PDF u objeto seleccionado;
- historial inferior tabular con seleccionar, renombrar, ocultar, eliminar y usar rectangulo como final.

`Guardar` conserva el estado de mediciones en `localStorage` por archivo y pagina. No agrega persistencia backend.

## Fase 4A/4B

La primera parte de Fase 4 agrega control fino sin cambiar el contrato JSON:

- `Deshacer` y `Rehacer` en la barra superior.
- Atajos `Ctrl+Z`, `Ctrl+Y` y `Ctrl+Shift+Z`.
- Historial reversible de hasta 50 estados para crear, mover, redimensionar, eliminar, renombrar, cambiar color/visibilidad, duplicar y cambiar medida final.
- Nudging con teclado: flechas `0.1 mm`, `Shift+flechas` `1 mm`, `Ctrl+flechas` `0.01 mm`.

El nudging mueve en milimetros exactos y no aplica snap automatico.

## Fase 4C

La Fase 4C limpia la experiencia visual sin agregar herramientas nuevas:

- la barra superior queda solo para acciones globales y zoom;
- las herramientas visuales quedan solo en el panel izquierdo;
- la informacion automatica del PDF queda solo en el inspector derecho;
- la barra inferior muestra herramienta activa, zoom, pagina y coordenadas;
- `Espacio + arrastrar` permite pan libre en X/Y como una aplicacion de escritorio.

## Fase 4D

La Fase 4D convierte las guias en objetos editables de trabajo:

- la herramienta `Guias` crea guias verticales con clic y horizontales con `Shift+clic`;
- las guias existentes se pueden seleccionar desde el visor;
- una guia seleccionada se resalta, aparece en el inspector y puede moverse con mouse;
- `Delete` borra la guia seleccionada;
- las flechas permiten nudging: `0.1 mm`, `Shift` para `1 mm` y `Ctrl` para `0.01 mm`;
- snap a guias sigue funcionando para lineas, rectangulos y coordenadas.

Las guias siguen siendo estado interno de trabajo y no agregan claves al JSON tecnico exportado.

Para correr solo el modulo:

```bash
python -m pdf_medidor_pro.dev_app
```

Luego abrir:

```text
http://127.0.0.1:5058/pdf-medidor-pro
```
