# Corrección V2 de compatibilidad de medida PDF/trim y etiquetas de slots

## 1. Alcance

Esta corrección posterior a la Fase 8P resuelve dos defectos sin cambiar `layout_schema_version`, el PDF fuente, las medidas del work, la geometría persistida ni la conexión productiva:

- falsos `SOURCE_TRIM_SIZE_MISMATCH` por conversión puntos/mm y redondeo normal;
- IDs Repeat completos superpuestos sobre el artwork del canvas.

## 2. Evidencia del job real

Job auditado: `ev2_5cf3e516add8b5be70249eed`.

Slot: `slot_repeat_ce9ebe01b64ced7a_0001`.

| Dato | Valor exacto |
| --- | --- |
| TrimBox seleccionado | `x=3.0000010555555554`, `y=3.0000010555555554`, `width=44.39992672222222`, `height=34.20006283333333 mm` |
| `work.trim_size_mm` | `width=44.4`, `height=34.2 mm` |
| `slot.geometry.trim_size_mm` | `width=44.4`, `height=34.2 mm` |
| Rotación intrínseca de página | `0°` |
| Rotación geométrica del slot | `0°` |
| Diferencia de ancho | `0.00007327777777987876 mm` |
| Diferencia de alto | `0.00006283333332390839 mm` |

El PDF físico declara:

```text
TrimBox [8.50394 8.50394 134.362 105.449] pt
```

`pdf_inspector.py` convierte con `25.4 / 72`. La UI propone después el work con tres decimales. No se encontró evidencia de caja incorrecta ni de PDF defectuoso.

## 3. Causa raíz y comparación corregida

`validate_output_capabilities()` usaba `DEFAULT_TOLERANCE_MM = 1e-9`, constante exclusiva del ruido matemático del kernel. La frontera de salida define ahora:

```text
PDF_BOX_TRIM_COMPATIBILITY_TOLERANCE_MM = 0.01
```

La comparación es componente a componente y acepta diferencias menores o iguales a `0.01 mm`. El margen de unidades de último lugar usado al evaluar exactamente el límite solo estabiliza la representación `float`; no amplía materialmente la tolerancia física.

Antes:

```text
44.39992672222222 vs 44.4 -> 0.00007327777777987876 > 1e-9 -> bloqueado
34.20006283333333 vs 34.2 -> 0.00006283333332390839 > 1e-9 -> bloqueado
```

Después se comparan los mismos valores y ambas diferencias son menores a `0.01 mm`. Una diferencia real mayor a la tolerancia continúa generando el issue. Al reevaluar el job auditado, los 17 mismatches presentes pasaron a 0 sin escribir el layout ni incrementar revisión.

## 4. Orientación y rotaciones

Las cajas PDF se conservan en coordenadas nativas. Para comparar el tamaño visible:

- rotación intrínseca `0/180`: `width × height`;
- rotación intrínseca `90/270`: `height × width`, solo como vista derivada.

No se intercambia ni reescribe `work.trim_size_mm` o `slot.geometry.trim_size_mm`. La rotación geométrica del slot Repeat/manual tampoco participa: su trim continúa persistido antes de esa rotación.

La salida temporal sigue bloqueando páginas rotadas mediante `UNSUPPORTED_INTRINSIC_ROTATION`, pero ya no agrega un mismatch de tamaño falso cuando la orientación coincide.

## 5. Agrupación de issues

`output_panel.js` agrupa issues de slot por nivel, código, asset y work. Muestra una sola fila con la cantidad afectada y un detalle desplegable con todos los IDs. La respuesta HTTP conserva issues individuales; la agrupación es solo presentación.

## 6. Etiquetas del canvas

- Etiqueta ordinal corta: `#1`, `#2`, etc.
- Tamaño compensado para zoom 35–400 %.
- Ocultación automática en slots físicamente pequeños o sin área visual suficiente.
- `pointer-events: none`, sin interferir con selección o drag.
- ID completo en tooltip, lista e inspector.
- Botón temporal `Etiquetas: sí/no`.

`showSlotLabels` vive fuera del layout. Cambiarlo no crea comando, dirty, autosave, revisión ni persistencia.

## 7. Cobertura

Python cubre igualdad exacta, conversión puntos/mm, dentro/fuera de tolerancia, rotación intrínseca 90/270, slot Repeat, slot manual y endpoint sin persistencia.

Node cubre agrupación de 30 issues, ordinales, slot pequeño, zoom 35/100/400 % y visibilidad temporal.

Playwright cubre 30 slots, zoom, agrupación desplegable, ocultación, ID completo en inspector, selección, drag y ausencia de persistencia por opciones visuales.

## 8. Límites

No se conecta preview/PDF, no se preparan físicamente páginas rotadas, no se modifica `content_transform`, no se corrigen PDFs, no se cambia Repeat y no se introduce una tolerancia mecánica general de imprenta. `0.01 mm` se limita a compatibilidad de medida de cajas PDF frente a trim en la frontera actual de salida.
