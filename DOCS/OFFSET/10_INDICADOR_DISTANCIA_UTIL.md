# 10 INDICADOR DISTANCIA UTIL

## Objetivo

Agregar una ayuda visual de precisión durante el arrastre manual de slots dentro del editor visual IA, sin tocar:

- backend
- motores de imposición
- contratos persistidos
- semántica de `repeat`, `nesting`, `hybrid`

## Alcance

Implementado en frontend:

- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`

No modifica `layout_constructor.json`.

## Comportamiento

Mientras el usuario arrastra un slot:

- aparece un indicador flotante cerca del slot
- se actualiza en tiempo real durante el movimiento
- desaparece al terminar el drag

### Ajuste de interacción posterior

Para evitar interferencia entre click y drag:

- el editor ahora usa un umbral mínimo de movimiento antes de considerar que empezó un drag real
- el indicador aparece solo después de superar ese umbral
- un click simple vuelve a seleccionar el slot normalmente
- al terminar un drag real, el slot arrastrado queda seleccionado

No bloquea:

- edición
- preview
- PDF

## Qué muestra

### 1. Distancia al margen útil más cercano

Calculada contra el área útil derivada de:

- `sheet_mm`
- `margins_mm`

Se evalúan estas distancias firmadas:

- izquierda útil
- derecha útil
- inferior útil
- superior útil

Se muestra la más cercana en valor absoluto.

### 2. Distancia al slot vecino más cercano

Se calcula:

- solo contra slots de la misma cara
- ignorando el slot arrastrado
- usando bounding boxes simples

Si no hay vecino válido:

- muestra `Sin vecino`

### 3. Distancia a zona de pinza

Si `ctp.enabled = true`, también muestra:

- distancia entre el borde inferior del slot y `ctp.gripper_mm`

La referencia sigue la implementación actual del editor, donde la pinza se interpreta en el borde inferior.

## Método de cálculo

### Bounding box simple

Usa:

- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`

No corrige por rotación real.

### Distancia entre slots

Se calcula con separación mínima entre rectángulos axis-aligned:

- `0 mm` si se tocan o superponen
- distancia euclidiana si están separados en diagonal

## Limitaciones

- no usa geometría rotada real
- no distingue trim vs caja final
- no conoce bleed/crop efectivos de salida
- en group move toma como referencia el slot activo del drag, no resume todo el grupo

## Beneficio práctico

Permite al operador:

- acercarse con más precisión a márgenes útiles
- estimar separación con el vecino más próximo
- controlar rápido la relación con la pinza CTP

sin depender de preview/PDF para cada microajuste manual.
