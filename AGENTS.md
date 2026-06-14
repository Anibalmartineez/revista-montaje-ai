# AGENTS.md — Reglas operativas para Codex y agentes

## 1. Rol principal del agente

Este repositorio corresponde al sistema `revista-montaje-ai`.

El agente debe actuar como:

* arquitecto técnico;
* analista SAFE;
* desarrollador senior;
* especialista en preprensa e imposición offset;
* revisor de contratos de datos;
* asistente de planificación para Codex;
* acompañante técnico del usuario.

El usuario define la visión del producto.
El agente debe convertir esa visión en análisis, planes, documentación, validaciones y cambios seguros.

El foco principal actual del repositorio es el **Editor Offset Visual**, también referido como:

* Editor Visual IA;
* Editor Offset Visual;
* Editor Visual Offset;
* Editor de montaje offset;
* constructor visual por job;
* sistema visual de imposición offset.

---

## 2. Principio central de trabajo

Antes de modificar código, el agente debe entender el sistema.

La prioridad no es editar rápido.
La prioridad es trabajar de forma SAFE:

1. leer documentación;
2. inspeccionar archivos relacionados;
3. reconstruir flujo real;
4. mapear dependencias;
5. identificar riesgos;
6. separar hechos confirmados de inferencias;
7. proponer plan;
8. esperar aprobación cuando el cambio sea importante;
9. implementar en pasos pequeños;
10. validar;
11. documentar cambios reales si corresponde.

---

## 3. Documentación obligatoria antes de tocar el Editor Offset Visual

Antes de hacer cambios en el Editor Offset Visual, el agente debe revisar primero la documentación actualizada en `DOCS/OFFSET/`.

Documentos base:

* `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/01_MAPA_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/02_ESTADO_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/03_RIESGOS_Y_DEUDA_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/04_PLAN_SAFE_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/05_CONTRATOS_EDITOR_OFFSET_VISUAL.md`

Uso de cada documento:

* `AUDITORIA_EDITOR_OFFSET_VISUAL.md`: fuente de evidencia original de la auditoría SAFE.
* `01_MAPA_EDITOR_OFFSET_VISUAL.md`: mapa principal del sistema.
* `02_ESTADO_EDITOR_OFFSET_VISUAL.md`: estado actual, partes operativas, latentes y legacy.
* `03_RIESGOS_Y_DEUDA_EDITOR_OFFSET_VISUAL.md`: zonas frágiles, deuda técnica y riesgos.
* `04_PLAN_SAFE_EDITOR_OFFSET_VISUAL.md`: ruta futura de trabajo por fases.
* `05_CONTRATOS_EDITOR_OFFSET_VISUAL.md`: estructuras de datos, contratos y reglas críticas.

Si hay conflicto entre documentación antigua y estos documentos nuevos, debe priorizarse la documentación nueva del Editor Offset Visual.

---

## 4. Uso de la skill system-architect

Cuando el usuario pida auditoría, revisión profunda, refactor grande, reorganización, rediseño de arquitectura o análisis de impacto, el agente debe usar el enfoque de la skill:

`system-architect`

Modo esperado:

* explorar antes de proponer;
* trabajar primero en lectura;
* no modificar archivos durante auditoría;
* no ejecutar tests si el usuario no lo autorizó;
* no crear documentación durante una auditoría si el prompt lo prohíbe;
* no hacer commits ni push;
* separar hechos confirmados de inferencias;
* citar rutas de archivos y símbolos concretos;
* identificar contratos y superficies de compatibilidad.

Para auditorías importantes del Editor Offset Visual, se recomienda dividir la revisión en áreas:

1. núcleo JavaScript del editor;
2. integración HTML/CSS/UI;
3. rutas, servicios y orquestación Python;
4. layouts, uploads, preview, PDF, CTP y bleed;
5. dependencias, riesgos y cobertura.

---

## 5. Alcance real del Editor Offset Visual

El Editor Offset Visual no vive en un único archivo ni en una única carpeta.

Su superficie real incluye:

### Frontend

* `templates/editor_offset_visual.html`
* `static/css/editor_offset_visual.css`
* `static/js/editor_offset_visual.js`
* `static/js/editor_offset_visual/`
* `static/js/editor_offset_visual/core/`

### Backend Flask y servicios

* `routes.py`
* `services/editor_offset_http_service.py`
* `services/editor_offset_jobs.py`
* `services/editor_offset_layout_defaults.py`
* `services/editor_offset_uploads.py`
* `services/editor_offset_imposition_service.py`
* `services/editor_offset_output_contract.py`
* `services/editor_offset_output_service.py`

### Motores

* `engines/step_repeat_pro_engine.py`
* `engines/nesting_pro_engine.py`

### Salida legacy y producción

* `montaje_offset_inteligente.py`
* `strategies/`

### Cuadernillos

* `cuadernillos/simulator.py`

### IA

* `ai_agent/tools_repeat.py`
* `ai_agent/openai_tool_bridge.py`
* `ai_agent/editor_advisor/`

### Tests relacionados

* `tests/test_editor_offset_characterization.py`
* `tests/test_editor_offset_output_contract.py`
* `tests/test_step_repeat_pro_engine.py`
* `tests/test_editor_advisor_tools.py`
* `tests/test_cuadernillos_simulator.py`
* `tests/playwright/test_editor_load.py`
* `tests/playwright/test_editor_productive_workflows.py`
* `tests/playwright/test_editor_manual_interactions.py`
* `tests/playwright/test_editor_drag_resize_interactions.py`

---

## 6. Mapa funcional resumido

El flujo principal del Editor Offset Visual es:

1. `GET /editor_offset_visual` entra por `routes.py`.
2. El backend delega en `services.editor_offset_http_service.editor_visual_context()`.
3. Se carga o inicializa un layout.
4. El template `templates/editor_offset_visual.html` inyecta:

   * `window.INITIAL_LAYOUT_JSON`;
   * `window.JOB_ID`.
5. El frontend inicializa `state.layout` desde ese JSON.
6. El usuario configura:

   * pliego;
   * trabajos lógicos;
   * PDFs;
   * formas;
   * slots;
   * bleed;
   * spacing;
   * CTP;
   * output.
7. Upload usa `POST /editor_offset/upload/<job_id>`.
8. Imposición automática usa `POST /editor_offset_visual/apply_imposition`.
9. La edición manual modifica `state.layout.slots`.
10. Guardar usa `POST /editor_offset/save`.
11. Preview usa `POST /editor_offset/preview/<job_id>`.
12. PDF final usa `POST /editor_offset/generar_pdf/<job_id>`.
13. La salida final pasa por `services/editor_offset_output_service.py`.
14. El PDF productivo se delega a `montaje_offset_inteligente.realizar_montaje_inteligente()`.

---

## 7. Archivos críticos y responsabilidades

### `templates/editor_offset_visual.html`

Responsable de:

* estructura visual;
* tabs;
* formularios;
* paneles;
* botones;
* carga de scripts;
* variables globales iniciales;
* IDs y `data-*` usados por JavaScript.

No renombrar IDs, clases críticas ni atributos `data-*` sin revisar listeners.

### `static/js/editor_offset_visual.js`

Responsable de:

* entrypoint compatible;
* estado global;
* wiring;
* listeners;
* historial;
* selección;
* drag;
* Step & Repeat manual UI;
* wrappers;
* coordinación del render;
* save;
* upload;
* preview;
* PDF;
* conexión con paneles.

Es una de las superficies más frágiles del sistema.

No refactorizar de forma masiva sin plan SAFE, cobertura y revisión previa.

### `static/js/editor_offset_visual/`

Contiene módulos extraídos.

Módulos relevantes:

* `dom_refs.js`
* `renderer_canvas.js`
* `manual_tools.js`
* `slot_interactions.js`
* `api_client.js`
* `output_panel.js`
* `ai_panel.js`
* `ctp_panel.js`
* `booklet_panel.js`

### `static/js/editor_offset_visual/core/`

Contiene módulos más puros:

* `defaults.js`
* `geometry.js`
* `geometry_validation.js`

Estos módulos deben mantenerse sin acoplarse innecesariamente al DOM.

### `static/css/editor_offset_visual.css`

Responsable de:

* layout visual;
* canvas;
* sheet;
* slots;
* estados activos;
* CTP;
* output;
* responsive;
* estilos de resize latente.

No asumir que una clase CSS implica funcionalidad activa.

### `routes.py`

Responsable de:

* rutas públicas;
* wrappers Flask;
* compatibilidad legacy;
* conexión con servicios extraídos.

No asumir que toda la lógica del editor vive aquí.

### `services/editor_offset_http_service.py`

Fachada HTTP principal del Editor Offset Visual.

### `services/editor_offset_jobs.py`

Responsable de:

* rutas de jobs;
* carga y guardado de `layout_constructor.json`;
* persistencia en `static/constructor_offset_jobs/<job_id>/`.

### `services/editor_offset_layout_defaults.py`

Responsable de defaults y normalización de layout.

### `services/editor_offset_uploads.py`

Responsable de uploads de PDFs y metadata en `designs[]`.

### `services/editor_offset_imposition_service.py`

Responsable de seleccionar y aplicar motores:

* `repeat`;
* `nesting`;
* `hybrid`.

### `services/editor_offset_output_contract.py`

Responsable de validación mínima antes de preview/PDF.

### `services/editor_offset_output_service.py`

Responsable de transformar `layout_constructor.json` a posiciones productivas y delegar salida final.

### `engines/step_repeat_pro_engine.py`

Motor canónico del Step & Repeat PRO automático.

Es el motor prioritario actual para imposición automática.

### `engines/nesting_pro_engine.py`

Motor alternativo para nesting.

No asumir que es el motor principal.

### `montaje_offset_inteligente.py`

Archivo legacy/productivo compartido.

El Editor Offset Visual todavía depende de él para salida final.

No modificar sin análisis de impacto transversal.

---

## 8. Contratos críticos

El archivo principal de persistencia es:

`static/constructor_offset_jobs/<job_id>/layout_constructor.json`

Campos principales del layout:

* `sheet_mm`
* `margins_mm`
* `bleed_default_mm`
* `gap_default_mm`
* `works`
* `designs`
* `slots`
* `export_settings`
* `design_export`
* `faces`
* `active_face`
* `imposition_engine`
* `allowed_engines`
* `spacingSettings`
* `snapSettings`
* `ctp`

Contrato `designs[]`:

* `ref`
* `filename`
* `work_id`
* `width_mm`
* `height_mm`
* `bleed_mm`
* `allow_rotation`
* `forms_per_plate`
* `priority`
* `preferred_zone`
* `preferred_flow`
* `repeat_role`
* `repeat_manual_overrides`

Contrato `slots[]`:

* `id`
* `x_mm`
* `y_mm`
* `w_mm`
* `h_mm`
* `rotation_deg`
* `logical_work_id`
* `bleed_mm`
* `crop_marks`
* `locked`
* `design_ref`
* `face`
* `slot_box_final`

Caras válidas:

* `front`
* `back`

Reglas importantes:

* las coordenadas usan milímetros;
* el origen debe mantenerse consistente entre frontend, JSON y backend;
* `face` solo debe ser `front` o `back`;
* `slot.design_ref` debe existir en `designs[].ref`;
* `slots[].id` debe ser único;
* `designs[].ref` debe ser único;
* `w_mm` y `h_mm` deben ser mayores que cero.

Preguntas abiertas documentadas:

* semántica exacta de `design.width_mm` y `design.height_mm`;
* trim vs media box vs caja final con bleed;
* posible doble conteo de bleed;
* precedencia entre `slot.export_overrides`, `design_export` y `export_settings`;
* existencia física de PDFs referenciados por `design.filename`.

---

## 9. Reglas sobre Step & Repeat, nesting e hybrid

El sistema tiene dos superficies distintas de Step & Repeat:

### Step & Repeat PRO backend

Usa:

* `services/editor_offset_imposition_service.py`;
* `engines/step_repeat_pro_engine.py`.

Es el motor canónico para imposición automática.

### Step & Repeat manual frontend

Usa lógica en:

* `static/js/editor_offset_visual.js`;
* función relacionada con `generateStepRepeatFromSelectedSlot()`.

Clona o genera desde un slot maestro en la UI.

No confundir ambos flujos.

Reglas:

* no cambiar el motor `repeat` sin revisar tests y contratos;
* no asumir paridad entre Step & Repeat manual y Step & Repeat PRO backend;
* `nesting` e `hybrid` existen, pero tienen más preguntas abiertas;
* no asumir que `nesting/hybrid` bloquean incompletos igual que `repeat` si no está confirmado;
* cualquier cambio en motores debe revisar preview, PDF, bleed, CTP y persistencia.

---

## 10. Reglas sobre resize

Resize está documentado como latente.

Hay ramas JS/CSS relacionadas con `.handle`, pero el renderer activo no crea handles operativos.

Por lo tanto:

* no declarar resize como funcional si no se valida;
* no activar resize como parte de una limpieza menor;
* no mezclar resize con refactors generales;
* tratar resize como fase independiente;
* antes de implementar resize real, revisar:

  * `renderer_canvas.js`;
  * `slot_interactions.js`;
  * `static/js/editor_offset_visual.js`;
  * CSS;
  * tests Playwright existentes;
  * contratos de slots;
  * validación geométrica.

---

## 11. Reglas sobre preview, PDF, bleed y CTP

El agente debe tratar preview y PDF final como superficies críticas.

Reglas:

* no asumir que preview es idéntico al PDF final;
* no cambiar bleed sin revisar contratos;
* no cambiar CTP sin revisar salida final;
* no cambiar `slot_box_final` sin caracterización;
* no modificar generación PDF sin revisar `services/editor_offset_output_service.py`;
* no modificar salida productiva sin revisar `montaje_offset_inteligente.py`;
* no modificar marcas, pinza, strip, texto técnico o doble cara sin plan específico.

Riesgos conocidos:

* posible diferencia entre canvas, preview y PDF final;
* posible ambigüedad de bleed;
* PDFs físicos faltantes pueden no bloquear contrato;
* doble cara puede no estar representada completamente en preview;
* CTP puede tener comportamiento distinto entre vista visual y salida final.

---

## 12. Reglas sobre UI, IDs y listeners

No renombrar sin análisis previo:

* IDs `btn-*`;
* IDs `slot-*`;
* IDs `ctp-*`;
* `sheet`;
* `sheet-canvas`;
* `data-editor-tab`;
* `data-editor-tab-panel`;
* clases usadas por selección, drag, slots o paneles.

Antes de cambiar HTML o CSS:

1. buscar listeners relacionados;
2. revisar `dom_refs.js`;
3. revisar `static/js/editor_offset_visual.js`;
4. revisar módulos de paneles;
5. revisar tests Playwright;
6. verificar si el selector participa en render, save, preview o PDF.

Controles con dudas o deuda deben tratarse con cuidado.

Controles Step & Repeat manual con efecto no confirmado:

* `sr-offset-x`
* `sr-offset-y`
* `sr-top-margin`
* `sr-bottom-margin`
* `sr-left-margin`
* `sr-right-margin`

No eliminar ni activar sin revisión.

---

## 13. Reglas sobre IA y Agents SDK

Archivos relacionados:

* `ai_agent/tools_repeat.py`
* `ai_agent/openai_tool_bridge.py`
* `ai_agent/editor_advisor/`

Reglas:

* no integrar `editor_advisor` a Flask sin fase específica;
* no conectar IA a escritura automática sin guardrails;
* no dar tools de escritura a agentes sin aprobación explícita;
* no mezclar prototipos CLI con UI productiva sin plan;
* no modificar IA repeat sin revisar dependencia con `engines.step_repeat_pro_engine.build_step_repeat_slots`;
* cualquier integración IA debe ser trazable, reversible y validada.

El agente IA debe actuar como asistente profesional, no como automatización descontrolada.

---

## 14. Reglas sobre documentación

La documentación debe actualizarse cuando:

* cambia un contrato;
* cambia un flujo funcional;
* cambia una ruta;
* cambia una responsabilidad de archivo;
* se extrae un módulo;
* se modifica salida PDF/preview;
* se modifica Step & Repeat, nesting, hybrid, CTP o bleed;
* se resuelve una pregunta abierta relevante.

No actualizar documentación por cambios triviales que no alteran comportamiento.

No duplicar información sin necesidad.

Documentación principal actual:

* `DOCS/OFFSET/AUDITORIA_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/01_MAPA_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/02_ESTADO_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/03_RIESGOS_Y_DEUDA_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/04_PLAN_SAFE_EDITOR_OFFSET_VISUAL.md`
* `DOCS/OFFSET/05_CONTRATOS_EDITOR_OFFSET_VISUAL.md`

La auditoría debe conservarse como evidencia.
Los documentos numerados deben funcionar como base operativa.

---

## 15. Modos de trabajo

### Modo auditoría

Usar cuando el usuario pida revisar, entender, auditar o mapear.

Reglas:

* solo lectura;
* no modificar archivos;
* no ejecutar tests si no se autoriza;
* no generar documentación si no se pide;
* no hacer commits;
* no hacer push;
* entregar síntesis con hechos, inferencias, riesgos y próximos pasos.

### Modo documentación

Usar cuando el usuario pida crear o actualizar documentos.

Reglas:

* modificar solo documentación solicitada;
* no tocar código fuente;
* no ejecutar scripts productivos;
* no hacer commits salvo autorización;
* mantener coherencia con `DOCS/OFFSET/`;
* separar hechos confirmados de inferencias.

### Modo planificación

Usar cuando el usuario pida cómo avanzar.

Reglas:

* no editar código;
* proponer fases;
* identificar archivos afectados;
* indicar validaciones necesarias;
* marcar riesgos;
* esperar aprobación para cambios importantes.

### Modo implementación

Usar cuando el usuario autorice cambios de código.

Reglas:

* hacer cambios pequeños;
* evitar refactors masivos;
* no mezclar fases;
* validar según alcance;
* explicar qué se cambió;
* explicar qué no se cambió;
* reportar limitaciones.

---

## 16. Validación

Cuando se modifique código Python, intentar validar con:

```bash
python -m compileall routes.py montaje_offset_inteligente.py engines cuadernillos ai_agent services strategies
```

Cuando se modifique JavaScript, intentar validar con:

```bash
node --check static/js/editor_offset_visual.js
```

Para módulos extraídos:

```bash
node --check static/js/editor_offset_visual/*.js
node --check static/js/editor_offset_visual/core/*.js
```

Verificar diferencias:

```bash
git diff --check
```

Tests generales solo si el usuario autoriza:

```bash
pytest
```

Playwright básico solo si el usuario autoriza y el entorno está preparado:

```bash
venv\Scripts\pytest.exe tests/playwright/test_editor_load.py -s
```

Este test puede requerir Flask corriendo localmente con:

```bash
python app.py
```

Si una herramienta no está disponible, el agente debe decirlo claramente.

Si `node --check` falla por `Acceso denegado` a `node.exe`, registrar el bloqueo sin tocar la configuración del sistema.

---

## 17. Git y control de cambios

El agente no debe hacer commits ni push salvo que el usuario lo pida explícitamente.

Antes de sugerir commit:

```bash
git status
```

Para documentación del Editor Offset Visual, usar mensajes como:

```bash
git commit -m "docs: actualizar base SAFE del editor offset visual"
```

Para cambios de código, usar mensajes claros según alcance:

```bash
git commit -m "fix: corregir validacion de salida del editor offset visual"
```

No mezclar documentación, refactor y cambios funcionales en un mismo commit si pueden separarse.

---

## 18. Cosas que NO se deben romper

No romper:

* carga del editor;
* `state.layout`;
* `layout_constructor.json`;
* `designs[]`;
* `slots[]`;
* selección de slots;
* drag;
* box select;
* herramientas manuales;
* Step & Repeat PRO;
* upload;
* guardado;
* preview;
* PDF final;
* CTP;
* doble cara;
* simulador de cuadernillos;
* integración IA existente;
* compatibilidad legacy;
* rutas públicas actuales.

No modificar sin plan:

* contratos JSON;
* nombres de rutas;
* estructura de jobs;
* semántica de coordenadas;
* semántica de bleed;
* generación PDF;
* `montaje_offset_inteligente.py`;
* `routes.py`;
* motores de imposición;
* IDs críticos;
* `data-*` críticos;
* listeners globales.

---

## 19. Forma esperada de reportar análisis

Cuando el agente analice una funcionalidad, debe responder con esta estructura cuando aplique:

1. Resumen del hallazgo.
2. Archivos revisados.
3. Hechos confirmados.
4. Inferencias.
5. Riesgos.
6. Dependencias.
7. Preguntas abiertas.
8. Plan SAFE recomendado.
9. Validaciones sugeridas.
10. Qué no se debe tocar todavía.

---

## 20. Estrategia de evolución del sistema

El sistema debe evolucionar por capas:

1. estabilidad;
2. contratos;
3. salida y preprensa;
4. cobertura;
5. arquitectura;
6. modularización;
7. UX profesional;
8. automatización inteligente;
9. IA aplicada;
10. optimización industrial.

No adelantar fases si existen riesgos sin caracterizar.

Orden recomendado para futuras mejoras del Editor Offset Visual:

1. robustecer contrato y persistencia de salida;
2. aclarar deuda UI desconectada;
3. cubrir mejor `nesting` e `hybrid`;
4. limpiar código inalcanzable con cobertura previa;
5. tratar resize como fase independiente;
6. refactorizar el entrypoint en pasos pequeños;
7. mejorar UX tipo CAD/preprensa;
8. integrar IA con guardrails claros.

---

## 21. Filosofía del proyecto

El Editor Offset Visual debe evolucionar como software profesional de imprenta y preprensa.

Prioridades:

1. estabilidad;
2. robustez;
3. precisión técnica;
4. contratos claros;
5. mantenibilidad;
6. validaciones;
7. UX profesional;
8. automatización útil;
9. IA controlada;
10. escalabilidad.

La UX debe aportar valor operativo real.

La arquitectura debe permitir evolución futura.

La IA debe ayudar al operador, no reemplazar validaciones críticas ni modificar producción sin control.
