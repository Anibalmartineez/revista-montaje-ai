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

## Validacion adicional en imposicion automatica Fase 5

Ademas de preview/PDF, el endpoint:

- `POST /editor_offset_visual/apply_imposition`

ahora tiene una validacion especifica para Step & Repeat PRO Inteligente.

### Regla

`forms_per_plate` ya no se trata como intencion blanda.

Para cada diseno, el motor calcula:

- `requested_forms`
- `placed_forms`
- `missing_forms`

Si algun diseno queda con `missing_forms > 0`:

- la imposicion falla
- no se acepta el montaje parcial
- el backend devuelve error bloqueante

### Error especifico

Implementado en `routes.py` como:

- `IncompleteImpositionError`

### Respuesta JSON esperada

```json
{
  "ok": false,
  "error": "No entran todas las formas solicitadas en el pliego. Diseno A: solicitadas 60, colocadas 30, faltan 30.",
  "details": [
    {
      "design_ref": "A",
      "filename": "diseno_a.pdf",
      "preferred_zone": "top",
      "requested_forms": 60,
      "placed_forms": 30,
      "missing_forms": 30
    }
  ]
}
```

### Garantias implementadas

- no se aplica layout incompleto en frontend si `ok: false`
- la generacion de slots por diseno es atomica
- no deben quedar slots parciales en una corrida fallida
- el backend trabaja sobre copia aislada del layout y fuerza regeneracion desde `designs[]`

### Casos Fase 5 cubiertos por la validacion estricta

La validacion aplica tambien cuando el motor intenta resolver:

- zonas verticales expandidas `top`, `bottom`, `center`
- varios disenos en una misma zona vertical (`top/top`, `bottom/bottom`, `center/center`)
- grupos `auto` compactados con zonas verticales explicitas
- `fill` inteligente al final

En todos los casos la regla final es la misma:

- si `placed_forms < requested_forms`, el layout no es valido
- el backend devuelve `ok: false`
- el frontend no reemplaza `state.layout`

### Validacion desde IA/tools

La tool `validar_repeat(layout)` ejecuta el motor y devuelve:

- `ok: true` si todas las formas solicitadas entran
- `ok: false` con el payload del error si el motor lanza `IncompleteImpositionError`

Las tools que generan layout (`generar_repeat`, `optimizar_repeat`) no deben ocultar ese error. Si el motor falla, la respuesta IA debe explicar el detalle y no devolver un layout aplicable.
