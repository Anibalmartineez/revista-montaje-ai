# 12 STEP REPEAT INTELIGENTE

## Objetivo de Fase 5

Volver mas util el motor automatico de Step & Repeat PRO del Editor Visual IA sin pasar a packing complejo ni romper la semantica consolidada de Fase 4.

Problema que resuelve:

- el motor `repeat` anterior trataba todos los disenos de forma demasiado lineal
- no habia preferencias claras por diseno
- la UI exponia demasiados controles tecnicos para algo que debia ser mas automatico
- al usar zonas preferidas podian quedar huecos grandes sin aprovechar
- podia aceptar montajes incompletos si no se validaba estrictamente la cantidad solicitada

## Estado final real en esta rama

La Fase 5 implementa:

- metadata por diseno para repeat
- `preferred_zone` como control principal visible
- `priority` automatico
- `repeat_role` automatico
- `preferred_flow` reservado pero inactivo
- `repeat_manual_overrides`
- zonas reales:
  - `top`
  - `bottom`
  - `left`
  - `right`
  - `center`
  - `auto`
- `fill` inteligente
- compactacion vertical segura de grupos zonales
- expansion vertical inteligente para `top/center/bottom`
- expansion vertical de una sola zona:
  - `top` anclado hacia arriba
  - `bottom` anclado hacia abajo
  - `center` centrado
- expansion vertical para multiples disenos dentro de la misma zona:
  - `top/top`
  - `bottom/bottom`
  - `center/center`
- compactacion final segura que integra `auto` con zonas verticales explicitas
- validacion estricta de formas solicitadas vs colocadas
- error bloqueante para montajes incompletos
- generacion atomica por diseno
- aislamiento de ejecuciones entre corridas
- capa IA/tools alineada con el motor Fase 5
- frontend IA con distincion `metadata_only` vs `layout_with_slots`

## Estado real del sistema Fase 5

### Que hace bien hoy

- respeta `forms_per_plate` como cantidad exacta
- falla con error claro si no entran todas las formas
- mantiene `auto/auto` como flujo legacy
- interpreta `preferred_zone` como preferencia de inicio, no como carcel rigida
- resuelve casos verticales comunes:
  - `top/bottom`
  - `top/center/bottom`
  - `center` solo
  - varios disenos en `top`
  - varios disenos en `bottom`
  - varios disenos en `center`
  - zona vertical + `auto`
- protege la salida final:
  - no cambia `slot.w_mm/h_mm`
  - no cambia `rotation_deg`
  - no toca preview/PDF

### Que no hace todavia

- no hace packing avanzado
- no tiene modo `maximize`
- no tiene sistema formal de modos
- no usa `preferred_flow`
- no expande horizontalmente `left/right`
- no compacta horizontalmente `left/right/center`
- `fill` sigue siendo heuristico

## Que ve hoy el usuario en la interfaz

En la lista de disenos, el usuario ve:

- `Formas/pliego`
- `Ancho`
- `Alto`
- `Bleed`
- `Permitir rotacion`
- `Ubicacion`

`Ubicacion` muestra textos amigables:

- `Automatico`
- `Arriba`
- `Abajo`
- `Izquierda`
- `Derecha`
- `Centro`

Internamente esos valores siguen siendo:

- `auto`
- `top`
- `bottom`
- `left`
- `right`
- `center`

`fill` no aparece como opcion visible en el select actual.

## Que queda automatico por detras

Ya no se expone en UI:

- `priority`
- `repeat_role`
- `preferred_flow`

Hoy el backend hace esto:

- `priority` se deriva automaticamente si no hay override manual
- `repeat_role` se deriva automaticamente si no hay override manual
- `preferred_flow` se conserva en contrato pero no se usa
- `forms_per_plate` se respeta como objetivo estricto

## Campos nuevos relevantes en `designs[]`

```json
{
  "priority": 1,
  "preferred_zone": "auto",
  "preferred_flow": "auto",
  "repeat_role": "secondary",
  "repeat_manual_overrides": {
    "priority": false,
    "preferred_flow": false,
    "repeat_role": false
  }
}
```

### Semantica actual

- `preferred_zone`
  - control principal visible
  - decide preferencia de inicio del grupo
- `priority`
  - orden interno de repeat
  - puede derivarse automaticamente
- `repeat_role`
  - `primary`, `secondary` o `fill`
  - puede derivarse automaticamente
- `preferred_flow`
  - reservado para futuro
  - hoy no afecta el motor
- `repeat_manual_overrides`
  - marca si ciertos campos repeat deben respetarse como override manual/historico

## Como funciona ahora el motor automatico

### 1. Normalizacion de disenos

Antes de imponer, el backend normaliza metadata de repeat por diseno y construye `repeat_manual_overrides`.

### 2. Derivacion automatica

Si no hay override manual:

- `priority` se deriva por ranking interno basado en `forms_per_plate`
- el diseno principal puede quedar como `primary`
- disenos menores pueden quedar como `secondary`
- `fill` se reserva para ocupar huecos restantes

Si un layout viejo trae valores manuales/historicos, se conservan.

### 3. Agrupacion por zona

Los disenos se agrupan por `preferred_zone`.

Orden de proceso real:

1. `top`
2. `left`
3. `center`
4. `right`
5. `bottom`
6. `auto`
7. `fill`

### 4. Zonas reales basicas

Las zonas ya no son una bandera decorativa. El motor define bandas simples dentro del area util:

- `top`: banda superior
- `bottom`: banda inferior
- `left`: banda izquierda en la zona media
- `right`: banda derecha en la zona media
- `center`: franja central
- `auto`: area util completa

Regla clave:

- las zonas actuan como preferencia de inicio, no como semantica nueva de slot

### 4.b Expansion vertical inteligente

Para `top`, `center` y `bottom` el flujo real ya no se queda solo con la banda inicial:

1. primero se intenta la zona preferida normal
2. si no entran todas las formas, el motor calcula si esos grupos caben como bloque vertical dentro del area util completa
3. si caben, reconstruye bounds expandidos y reintenta
4. luego vuelve a compactar verticalmente

Esto corrige casos donde:

- `auto/auto` entraba
- pero `bottom/top` fallaba injustificadamente por rigidez de bandas
- `center` fallaba aunque en `auto` entrara
- varios disenos en `top` o `bottom` quedaban atrapados en su banda inicial

### 4.c Expansion de una sola zona vertical

Cuando una sola zona vertical contiene uno o varios disenos y la banda inicial no alcanza, el motor puede calcular un bounds expandido usando mas altura del area util.

Anclajes actuales:

- `top`: bloque expandido hacia arriba
- `bottom`: bloque expandido hacia abajo
- `center`: bloque expandido centrado

Esto mantiene la intencion de ubicacion sin convertir la zona en packing libre.

### 5. Fill inteligente

Los disenos `fill` se procesan al final.

Que hace:

- no mueve los grupos ya colocados
- recorre candidatos sobre el area util restante
- prueba varias trayectorias simples
- coloca solo donde entra sin colision
- mantiene spacing, bleed y orientacion actuales

Que no hace:

- nesting avanzado
- packing matematico
- redistribucion total del layout

### 6. Compactacion vertical segura

Despues de crear grupos zonales explicitos, el backend intenta compactar:

- `top + bottom`
- `top + center + bottom`
- `top`, `center` o `bottom` con `auto` en una compactacion final segura

La compactacion:

- calcula bbox de cada grupo
- intenta formar un bloque vertical mas compacto
- mantiene una separacion minima vertical
- no sale del area util
- no permite colisiones
- si no es segura, deja el layout original

Esto mejora casos donde `top` y `bottom` dejaban demasiado vacio en el centro.

### 6.c Integracion de `auto` con zonas verticales

Si hay zonas verticales explicitas y tambien disenos `auto`, el flujo real es:

1. generar zonas explicitas
2. aplicar expansion/compactacion vertical zonal si hace falta
3. generar `auto` evitando colisiones
4. registrar el rango de slots generado por `auto`
5. intentar una compactacion final segura de:
   - `top`
   - `center`
   - `bottom`
   - `auto`

Si todos los disenos estan en `auto`, este paso no corre y se conserva el comportamiento legacy.

### 6.b Diferencia entre compactacion y expansion

- compactacion vertical:
  - acerca grupos ya colocados
  - no cambia el area originalmente asignada a la zona
- expansion vertical:
  - se usa cuando `top/center/bottom` no entran completos en la banda inicial
  - les permite usar mas altura del area util si geometricamente cabe
  - sigue siendo segura: no sale del area util ni acepta colisiones

### 7. Validacion estricta de formas

El motor ya no acepta montajes incompletos silenciosamente.

Por cada diseno calcula:

- `requested_forms`
- `placed_forms`
- `missing_forms`

Si algun diseno queda incompleto:

- se lanza `IncompleteImpositionError`
- `apply_imposition` responde:
  - `ok: false`
  - `error`
  - `details`
- el frontend no debe reemplazar `state.layout`

### 8. Generacion atomica y aislamiento

Cada diseno arma primero sus slots en una lista local.

Solo cuando ese diseno entra completo:

- sus slots se agregan al resultado final

Ademas:

- la ejecucion del motor trabaja sobre copia aislada del layout
- se limpia `slots` antes de regenerar
- un error anterior no debe contaminar la siguiente corrida

Flujo ya validado en pruebas sinteticas:

- `auto/auto` OK
- `bottom/top` OK si geometricamente cabe tras expansion
- volver a `auto/auto` OK
- si no entra realmente, el motor falla con detalle por diseno

## Capa IA y tools Fase 5

### Tools disponibles relevantes

- `analizar_layout(layout)`
- `generar_repeat(layout, config)`
- `optimizar_repeat(layout)`
- `centrar_layout(layout)`
- `aplicar_reglas_repeat(layout, reglas)`
- `set_design_zone(layout, design_ref, preferred_zone)`
- `set_design_zones(layout, zones_by_design)`
- `validar_repeat(layout)`

### Flujo real

1. El usuario escribe un prompt en el panel IA.
2. El frontend envia `prompt` y `layout_json`.
3. `openai_tool_bridge.py` decide o ejecuta tools locales.
4. Las tools llaman al motor real de `routes.py` cuando hay que generar repeat.
5. La respuesta devuelve:
   - mensaje
   - tools usadas
   - layout sugerido si corresponde
   - analisis o errores
6. El frontend solo aplica el layout si el usuario confirma con `Aplicar cambios`.

### Capacidades actuales

- cambiar una zona con `set_design_zone`
- cambiar varias zonas con `set_design_zones`
- regenerar Step & Repeat despues de cambiar zonas
- validar sin aplicar
- interpretar `IncompleteImpositionError`
- hacer retry controlado en `optimizar_repeat` reseteando zonas explicitas a `auto` si corresponde
- identificar disenos por:
  - `ref`
  - `filename`
  - `work_id`
  - dimensiones tipo `50x40`

### Fixes IA ya incorporados

- se preserva el ultimo layout generado aunque luego se ejecute una tool de analisis
- prompts con multiples zonas pueden usar `set_design_zones`
- si el prompt pide generar/repetir/montaje, se ejecuta `generar_repeat` despues de cambiar zonas
- si solo se cambia metadata, no se promete un montaje regenerado

## Frontend IA

El frontend distingue:

- `metadata_only`
  - cambia preferencias del layout
  - no regenera slots
  - muestra mensaje de preferencias listas
- `layout_with_slots`
  - trae slots recalculados
  - muestra cambios listos para aplicar

Tambien muestra la cadena de tools usadas cuando el backend la devuelve.

## Semanticas que NO cambiaron

Se mantienen congeladas:

- `slot.w_mm / slot.h_mm` = footprint final del slot en `repeat`
- `rotation_deg` = orientacion del contenido
- preview/PDF y `montaje_offset_inteligente.py` no cambian su semantica por Fase 5

## Compatibilidad con layouts viejos

La Fase 5 mantiene compatibilidad:

- layouts sin metadata nueva siguen funcionando
- `preferred_zone` faltante cae a `auto`
- `priority` y `repeat_role` pueden derivarse automaticamente
- `preferred_flow` historico se conserva si existe
- `repeat_manual_overrides` se puede reconstruir al normalizar

## Limitaciones actuales

- no hay compactacion horizontal para `left/center/right`
- no hay expansion horizontal equivalente para `left/right`
- no hay packing avanzado
- `preferred_flow` no funciona todavia
- `fill` mejoro mucho el aprovechamiento de huecos, pero sigue siendo heuristico
- la heuristica de `repeat_role` automatico puede requerir ajuste con casos reales
- no existe modo `maximize`
- no hay sistema formal de modos

## Proximos pasos recomendados

1. Agregar pruebas de regresion para casos zonales y `fill`.
2. Agregar pruebas de regresion para:
   - `requested_forms / placed_forms / missing_forms`
   - `IncompleteImpositionError`
   - reruns despues de error
3. Medir con ejemplos reales si conviene ajustar heuristica de `repeat_role`.
4. Evaluar compactacion o expansion horizontal segura.
5. Mantener a la IA trabajando sobre:
   - `forms_per_plate`
   - `preferred_zone`
   - reglas repeat estables

## Proximos pasos agregados tras la ultima auditoria

- agregar pruebas para IA/tools:
  - multiples zonas en un prompt
  - `set_design_zones` seguido de `generar_repeat`
  - errores `IncompleteImpositionError`
  - `metadata_only` vs `layout_with_slots`
- evaluar sistema de modos (`exact`, `maximize`) solo con contrato y tests
- mantener `preferred_flow` documentado como reservado hasta que exista implementacion real
- recien en una fase posterior evaluar packing mas avanzado si sigue haciendo falta
