# Reporte de correccion: eje Y del Preview PNG del Editor Offset Visual

## 1. Bug corregido

Se corrigio el bug de eje Y invertido en el Preview PNG del Editor Offset Visual.

El preview raster ahora convierte `y_mm` desde coordenadas con origen inferior izquierdo, usadas por el canvas y el PDF final, a coordenadas PIL con origen superior izquierdo.

## 2. Causa raiz

La funcion `generar_preview_pliego()` pegaba cada pieza en la imagen PIL usando directamente:

```python
y_px = mm_to_px(pos["y_mm"], dpi)
canvas_img.paste(scaled, (x_px, y_px))
```

Ese calculo interpretaba `y_mm` como distancia desde arriba, aunque el editor visual usa `bottom` en CSS y el PDF final usa ReportLab, ambos con semantica de origen inferior izquierdo.

La correccion aplicada mantiene `x_px` igual y convierte `y_px` considerando el alto del pliego y el alto real de la imagen ya renderizada:

```python
y_px = H - mm_to_px(pos["y_mm"], dpi) - scaled.height
```

Esto evita que lo que esta abajo en canvas aparezca arriba en preview, y viceversa.

## 3. Archivos modificados

- `montaje_offset_inteligente.py`
  - Funcion modificada: `generar_preview_pliego()`.
  - Cambio: conversion de coordenada Y antes de `canvas_img.paste(...)`.

- `tests/test_editor_offset_characterization.py`
  - Se agrego helper `_solid_pdf()`.
  - Se agrego prueba `test_preview_png_keeps_bottom_left_slot_y_semantics()`.
  - La prueba genera dos PDFs solidos y los coloca en dos slots verticales:
    - un slot abajo;
    - un slot arriba.
  - Luego verifica que el preview PNG conserve el orden vertical esperado.

## 4. Tests ejecutados

Se ejecutaron solo tests relacionados:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_characterization.py -q
```

Resultado:

```text
12 passed
```

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_editor_offset_output_contract.py -q
```

Resultado:

```text
7 passed
```

Como el cambio usa `scaled.height`, que tambien cubre el caso rotado en preview, se ejecuto tambien:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_step_repeat_pro_engine.py -q
```

Resultado:

```text
14 passed
```

## 5. Resultado de verificacion manual

No se ejecuto verificacion manual desde navegador en esta fase.

Verificacion manual sugerida cuando Flask este corriendo:

1. Abrir `http://127.0.0.1:5000/editor_offset_visual`.
2. Cargar o crear un job con varios slots en filas verticales.
3. Generar Preview.
4. Generar PDF final.
5. Comparar Canvas vs Preview vs PDF.
6. Confirmar que lo de arriba queda arriba.
7. Confirmar que lo de abajo queda abajo.
8. Confirmar que el PDF final no empeoro.
9. Confirmar que no cambio el comportamiento de sangrado.

## 6. Riesgos pendientes

Siguen pendientes problemas detectados en la auditoria previa:

- Posible doble conteo de sangrado.
- Contrato ambiguo de `design.width_mm/height_mm`.
- Diferencias entre medida final, `MediaBox`, `TrimBox`, `BleedBox` y bleed configurado.
- Validacion geometrica frontend no bloqueante para preview/PDF.
- Resultado de `saveLayout()` no verificado antes de generar salida.
- PDF final sin cache busting equivalente al preview.
- Riesgos alrededor de `slot_box_final`.

No se tocaron en esta correccion:

- PDF final.
- Upload.
- Motores repeat, nesting o hybrid.
- Contrato de sangrado.
- `slot_box_final`.
- CTP.
- Rutas publicas.

## 7. Proximo paso recomendado

Realizar verificacion manual con un job real o controlado que contenga slots arriba y abajo, comparando Canvas, Preview y PDF final.

Despues, abordar en una fase separada el contrato de sangrado y el posible doble conteo, sin mezclarlo con la correccion del eje Y del preview.
