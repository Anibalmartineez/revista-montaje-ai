# 01 - Arquitectura PDF Medidor Pro

## Resumen

PDF Medidor Pro es un modulo hermano de `sistema_presupuesto` y de las superficies del editor offset. Su objetivo es medir PDFs de forma independiente, con una integracion Flask minima.

## Decision arquitectonica

La inspeccion del repositorio mostro que:

- `app.py` compone la aplicacion Flask principal.
- `routes.py` concentra rutas legacy y del Editor Offset Visual.
- `sistema_presupuesto` funciona como modulo aislado con blueprint y frontend interno.

Por eso PDF Medidor Pro sigue el patron de modulo aislado:

- `pdf_medidor_pro/api.py` define el blueprint.
- `pdf_medidor_pro/services/` contiene logica backend sin depender de `routes.py`.
- `pdf_medidor_pro/templates/` y `pdf_medidor_pro/static/` contienen la UI propia.
- `app.py` solo registra el blueprint.

## Flujo funcional

1. El usuario abre `/pdf-medidor-pro`.
2. El frontend carga CSS/JS del modulo.
3. El usuario sube un PDF a `/api/pdf-medidor-pro/upload`.
4. El backend valida extension, guarda con UUID y analiza cajas con PyMuPDF.
5. El backend renderiza la primera pagina a PNG.
6. El frontend muestra cajas automaticas y preview.
7. El usuario mide lineas, rectangulo final y calibra escala si hace falta.
8. El frontend envia el contrato a `/api/pdf-medidor-pro/export`.
9. El backend normaliza y guarda un JSON tecnico.

## Contencion

No depende de:

- `routes.py`
- `sistema_presupuesto/`
- Editor Offset Visual
- `DOCS/OFFSET/`
- motores de montaje

Las carpetas `uploads/`, `previews/` y `exports/` son runtime y no deben versionar archivos generados.
