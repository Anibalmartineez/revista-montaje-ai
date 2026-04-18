# 08 VALIDACION SALIDA

## Objetivo

Documentar la validación mínima incorporada antes de generar:

- `POST /editor_offset/preview/<job_id>`
- `POST /editor_offset/generar_pdf/<job_id>`

## Ubicación elegida

La validación se ubicó en `routes.py`, en el helper:

- `_validate_constructor_output_layout(layout)`

## Por qué ahí

- es el punto más cercano a preview/PDF sin tocar motores
- permite bloquear layouts inválidos antes de entrar en `montar_offset_desde_layout()`
- no cambia la semántica de `repeat`, `nesting`, `hybrid`
- no modifica la lógica de bleed/crop
- no afecta rutas legacy que no usan estos endpoints

## Endpoints cubiertos

### Preview

- `routes.editor_offset_preview`

### PDF final

- `routes.editor_offset_generar_pdf`

Ambos ahora:

1. cargan el layout persistido
2. ejecutan `_validate_constructor_output_layout(layout)`
3. si hay errores:
   - devuelven `422`
   - respuesta JSON estructurada
4. si solo hay warnings:
   - generan salida normalmente
   - devuelven `warnings[]` en la respuesta JSON

## Errores que bloquean preview/PDF

### Diseño

- `designs[].ref` faltante
- `designs[].ref` duplicado
- diseño no representado como objeto JSON válido

### Slot

- `slots[].id` faltante
- `slots[].id` duplicado
- `slots[].design_ref` faltante
- `slots[].design_ref` inexistente en `designs[].ref`
- `slot.face` distinto de `front` o `back`
- `x_mm` no numérico o ausente
- `y_mm` no numérico o ausente
- `w_mm` no numérico o ausente
- `h_mm` no numérico o ausente
- `bleed_mm` no numérico o ausente
- `rotation_deg` no numérico o ausente
- `w_mm <= 0`
- `h_mm <= 0`
- slot no representado como objeto JSON válido

## Warnings que no bloquean salida

- `logical_work_id` no resuelve contra `works[].id`
- `faces[]` contiene `back` pero no existen slots `face="back"`

## Formato de respuesta

### Error bloqueante

```json
{
  "ok": false,
  "error": "El layout contiene errores de contrato y no se puede generar la preview.",
  "errors": [
    {
      "level": "error",
      "code": "slot_design_ref_invalid",
      "message": "Cada slot debe apuntar a un design_ref existente en designs[].ref.",
      "path": "slots[2].design_ref"
    }
  ],
  "warnings": []
}
```

### Salida válida con warnings

```json
{
  "ok": true,
  "url": "/static/constructor_offset_jobs/<job_id>/preview.png",
  "warnings": [
    {
      "level": "warning",
      "code": "back_face_without_slots",
      "message": "El layout declara la cara 'back' en faces[], pero no hay slots con face='back'.",
      "path": "faces"
    }
  ]
}
```

## Comportamiento del frontend

`static/js/editor_offset_visual.js` ahora:

- muestra alert si preview/PDF fallan por errores de contrato
- lista mensajes de `errors[]`
- también lista `warnings[]` si el backend los devuelve
- si la salida fue exitosa con warnings, los muestra después de generar preview/PDF

## Alcance intencionalmente limitado

Esta validación no intenta todavía:

- validar semántica geométrica profunda por engine
- validar consistencia visual de rotación
- validar bleed/crop a nivel de interpretación final
- reescribir el contrato
- refactorizar motores legacy

## Beneficio concreto

Se elimina la omisión silenciosa de slots inválidos en los dos flujos más sensibles:

- preview
- PDF final

Ahora el sistema falla de forma explícita cuando el contrato persistido ya no alcanza para producir una salida confiable.
