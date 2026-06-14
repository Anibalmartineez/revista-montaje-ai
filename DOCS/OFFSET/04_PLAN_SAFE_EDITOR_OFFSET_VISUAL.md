# Plan SAFE Editor Offset Visual

Fuente principal: `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`.

Este documento transforma la auditoria en una ruta SAFE futura. No autoriza implementacion directa.

## Principios

### Hechos confirmados

El Editor Offset Visual tiene superficies productivas sensibles:

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/`
- `static/css/editor_offset_visual.css`
- `routes.py`
- `services/editor_offset_*.py`
- `engines/step_repeat_pro_engine.py`
- `engines/nesting_pro_engine.py`
- `montaje_offset_inteligente.py`
- `static/constructor_offset_jobs/<job_id>/layout_constructor.json`

### Reglas SAFE

- No cambiar contratos sin caracterizacion previa.
- No tocar `montaje_offset_inteligente.py` sin auditoria de flujos legacy.
- No activar resize como parte de una limpieza incidental.
- No renombrar IDs, `data-*` o clases dinamicas sin revisar listeners.
- No limpiar codigo inalcanzable sin cobertura de comportamiento.
- No tratar `nesting/hybrid` como equivalentes a `repeat` sin validar formas incompletas.

## Fase 1: Congelar contratos criticos

### Objetivo

Caracterizar el contrato actual antes de corregir o refactorizar.

### Alcance

Documentar o proponer caracterizacion para:

- dimensiones de `designs[]`
- dimensiones de `slots[]`
- `bleed`
- `has_bleed`
- `slot_box_final`
- `forms_per_plate`
- `faces` `front/back`
- CTP
- PDF faltante
- preview vs PDF final

### Archivos criticos

- `services/editor_offset_output_contract.py`
- `services/editor_offset_output_service.py`
- `services/editor_offset_uploads.py`
- `services/editor_offset_layout_defaults.py`
- `engines/step_repeat_pro_engine.py`
- `static/js/editor_offset_visual.js`

### No tocar primero

- `montaje_offset_inteligente.py`
- contratos persistidos sin caracterizacion
- salida PDF productiva

### Requiere verificacion

- significado real de `design.width_mm/height_mm`
- existencia fisica de PDFs
- precedencia de export/bleed/crop

## Fase 2: Matriz UI y controles

### Objetivo

Separar UI activa, UI desconectada y UI riesgosa antes de cambiar template o listeners.

### Clasificar

- controles conectados
- controles visibles sin efecto confirmado
- listeners opcionales sin DOM
- copy desalineado
- botones que no deben renombrarse
- IDs criticos
- `data-*` criticos
- clases dinamicas criticas

### Archivos criticos

- `templates/editor_offset_visual.html`
- `static/js/editor_offset_visual.js`
- `static/css/editor_offset_visual.css`
- `static/js/editor_offset_visual/dom_refs.js`

### No tocar primero

- IDs `btn-*`, `slot-*`, `ctp-*`, `ai-*`
- `data-editor-tab`
- `data-editor-tab-panel`
- `sheet`
- `sheet-canvas`

## Fase 3: Matriz entrypoint vs modulos

### Objetivo

Entender que responsabilidades siguen en `static/js/editor_offset_visual.js` y cuales ya fueron extraidas.

### Documentar

- responsabilidades que siguen en `static/js/editor_offset_visual.js`
- responsabilidades ya extraidas
- wrappers que delegan
- codigo inalcanzable
- funciones posiblemente huerfanas
- candidatos futuros a extraccion

### Archivos criticos

- `static/js/editor_offset_visual.js`
- `static/js/editor_offset_visual/*.js`
- `static/js/editor_offset_visual/core/*.js`
- `templates/editor_offset_visual.html`

### Requiere caracterizacion previa

- carga inicial
- tabs
- seleccion
- multiseleccion
- box select
- drag
- spacing live
- Step & Repeat manual
- save
- apply imposition
- preview/PDF
- cuadernillos
- CTP

## Fase 4: Auditoria de salida y preprensa

### Objetivo

Caracterizar salida productiva antes de tocar preview/PDF, bleed, CTP o legacy.

### Caracterizar

- existencia fisica de PDFs
- precedencia de bleed
- crop marks
- `export_settings`
- `design_export`
- `slot.export_overrides`
- CTP marks
- CTP strip
- texto tecnico
- doble cara
- paridad canvas-preview-PDF
- `vector_hybrid`

### Archivos criticos

- `services/editor_offset_output_service.py`
- `services/editor_offset_output_contract.py`
- `montaje_offset_inteligente.py`
- `strategies/*`
- `static/js/editor_offset_visual/output_panel.js`
- `static/js/editor_offset_visual/ctp_panel.js`

### No tocar primero

- render legacy en `montaje_offset_inteligente.py`
- estrategias compartidas
- contrato de salida sin tests

## Fase 5: Implementacion futura en cambios pequenos

### Orden recomendado

1. Robustecer contrato y persistencia de salida.
2. Aclarar deuda UI desconectada.
3. Cubrir `nesting/hybrid`.
4. Limpiar codigo inalcanzable solo con cobertura previa.
5. Tratar resize como fase independiente.
6. Refactorizar entrypoint en pasos pequenos y reversibles.

### Cambios que necesitan auditoria previa con system-architect

- cambios en `layout_constructor.json`
- cambios en `slots[]`
- cambios en `designs[]`
- cambios en bleed/dimensiones
- cambios en `routes.py`
- cambios en `montaje_offset_inteligente.py`
- cambios en preview/PDF
- activacion de resize
- integracion nueva de IA
- cambios de IDs o `data-*`

## Validacion futura recomendada

No ejecutada durante esta documentacion. Cuando exista una fase aprobada, considerar:

- `python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies`
- `git diff --check`
- `node --check static/js/editor_offset_visual.js`
- `node --check static/js/editor_offset_visual/*.js`
- `node --check static/js/editor_offset_visual/core/*.js`
- tests unitarios focalizados
- Playwright focalizado para UI productiva

## Preguntas abiertas

- Que cambios deben ser contractuales y versionados?
- Que layouts historicos se deben preservar?
- Que nivel de fidelidad debe tener preview frente a PDF final?
- Debe `nesting/hybrid` bloquear layouts incompletos?
- Que UI desconectada se debe activar, ocultar o documentar?

## Inferencias

La ruta mas segura es caracterizar primero contrato y salida, luego resolver UI desconectada, y solo despues limpiar o refactorizar.
