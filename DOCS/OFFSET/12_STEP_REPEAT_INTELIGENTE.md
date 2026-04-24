# 12 STEP REPEAT INTELIGENTE

## Objetivo de Fase 5

Volver mas util el motor automatico de Step & Repeat PRO del Editor Visual IA sin pasar a packing complejo ni romper la semantica consolidada de Fase 4.

Problema que resuelve:

- el motor `repeat` anterior trataba todos los disenos de forma demasiado lineal
- no habia preferencias claras por diseno
- la UI exponia demasiados controles tecnicos para algo que debia ser mas automatico
- al usar zonas preferidas podian quedar huecos grandes sin aprovechar

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

La compactacion:

- calcula bbox de cada grupo
- intenta formar un bloque vertical mas compacto
- mantiene una separacion minima vertical
- no sale del area util
- no permite colisiones
- si no es segura, deja el layout original

Esto mejora casos donde `top` y `bottom` dejaban demasiado vacio en el centro.

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
- no hay packing avanzado
- `preferred_flow` no funciona todavia
- `fill` mejoro mucho el aprovechamiento de huecos, pero sigue siendo heuristico
- la heuristica de `repeat_role` automatico puede requerir ajuste con casos reales

## Proximos pasos recomendados

1. Agregar pruebas de regresion para casos zonales y `fill`.
2. Medir con ejemplos reales si conviene ajustar heuristica de `repeat_role`.
3. Evaluar compactacion horizontal segura.
4. Mantener a la IA trabajando sobre:
   - `forms_per_plate`
   - `preferred_zone`
   - reglas repeat estables
5. Reci en una fase posterior evaluar packing mas avanzado si sigue haciendo falta.
