# Fase 31 — PDF V2 propio detrás de gate

Fecha de corte: 2026-09-11.

Esta fase incorpora una ruta PDF propia de V2, separada del puente y del renderer legacy. El gate `EDITOR_OFFSET_V2_PDF_FINAL_ENABLED` queda apagado por defecto.

## 1. Ruta y contrato

```text
POST /api/editor-offset-v2/jobs/<job_id>/pdf-final
```

La solicitud acepta `face` (`front`, `back` o `both`), `dpi` y `allow_mirror_bleed`. La salida se publica atómicamente bajo `outputs/` con nombre ligado a revisión, cara y resolución. La generación no modifica Layout V2, assets ni revisiones.

Cuando se solicitan ambas caras se generan dos páginas en el orden declarado por el layout. Cada página conserva el tamaño físico de la hoja en milímetros convertido a puntos PDF.

## 2. Propiedad V2 y seguridad

El servicio vive en `editor_offset_v2/application/pdf_final_service.py` y no importa módulos de negocio V1. Reutiliza la preparación física y el compositor de Preview propios de V2; el gate de Preview no necesita estar activado para producir el artefacto gated.

Los errores de Preview, identidad física, cajas, transformaciones, marcas o caras bloquean la generación y no dejan un PDF parcial.

## 3. Estado del renderer

El artefacto de esta fase es un **PDF candidato rasterizado**: cada página contiene la composición PNG de V2 a la resolución solicitada. Esto permite verificar páginas, dimensiones, orden, transforms, clipping, bleed, marcas de corte y flip dentro de una frontera propia y reversible.

Todavía no se declara preservación vectorial ni aprobación productiva. La política `preserve_vector_content`, color, fuentes, perfiles, sobreimpresión y tolerancias de imprenta requieren un renderer vectorial V2 y una fase de cierre posterior.

## 4. Validación

Prueba focalizada:

```text
venv\Scripts\python.exe -m pytest tests/editor_offset_v2/test_pdf_final_v2.py -q
3 passed
```

Suite Python V2:

```text
venv\Scripts\python.exe -m pytest tests/editor_offset_v2 -q
425 passed, 1 omitido
```

La prueba inspecciona el PDF generado, verifica el número de páginas, las dimensiones físicas del pliego, la presencia de contenido y la publicación bajo `outputs/`. También se renderizó una página con Poppler para comprobación visual.

## 5. Límites y siguiente decisión

El endpoint permanece bloqueado en despliegues normales. Antes de habilitarlo como salida productiva hay que reemplazar o complementar el compositor raster con una ruta vectorial, fijar cajas PDF de hoja, color y fuentes, comparar canvas–Preview–PDF con tolerancias aprobadas y conectar el preflight como condición obligatoria. CTP y su contrato de marcas siguen fuera de alcance.
