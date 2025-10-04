# Auditoría del diagnóstico flexográfico

## Resumen ejecutivo
- Se centralizaron los umbrales críticos (texto mínimo, trazo, TAC, sangrado) en `flexo_config.py` y se eliminaron hardcodes dispersos.
- Las reglas de `advertencias_disenio`, `simulador_riesgos`, `preview_tecnico` y `reporte_tecnico` ahora consumen los umbrales configurados garantizando coherencia entre backend y reportes.
- El overlay HTML (`resultado_flexo.html`) recalcula los bounding boxes usando `getBoundingClientRect`, corrigiendo desalineaciones en la vista web.
- Se añadieron pruebas unitarias para validar límites (texto 4 pt, trazos mínimos, perfiles de material/anilox) y la lógica de escalado en el template.
- Se incorporó el script `tools/audit_flexo.py` para detectar futuros hardcodes y patrones obsoletos.

## Hallazgos por severidad
### Alta
- **Inconsistencia de umbrales** (resuelta): múltiples módulos replicaban `4 pt`, `0.25 pt`, `3 mm` y límites de TAC → reemplazados por `flexo_config.get_flexo_thresholds`.
- **Overlay desfasado en la UI** (resuelto): el cálculo `clientWidth/naturalWidth` ignoraba cambios de layout, provocando desalineaciones de advertencias.

### Media
- **Tramas débiles**: `montaje_flexo.detectar_tramas_débiles` mantiene umbrales fijos (5 % y 2 % del área). Recomendado parametrizarlos con `flexo_config` en una iteración futura.
- **Cálculo de TAC local**: no existe aún un hook para “hot spots” por región. Se sugiere aprovechar el nuevo módulo de configuración para habilitarlo posteriormente.

### Baja
- **Scripting**: `tools/audit_flexo.py` aún no revisa claves JSON/backend ↔ frontend; ampliarlo permitiría auditar discrepancias en `advertencias_iconos` y campos derivados.
- **Documentación**: complementar README con guía para actualizar perfiles de `flexo_config` cuando se agreguen nuevos materiales/anilox.

## Cambios relevantes
- Nuevo módulo `flexo_config.py` con dataclass `FlexoThresholds` y función `get_flexo_thresholds(material, anilox_lpi)`.
- Refactor de `advertencias_disenio.py`, `simulador_riesgos.py`, `preview_tecnico.py` y `reporte_tecnico.py` para usar la configuración centralizada.
- Ajuste de `templates/resultado_flexo.html` para escalar bboxes con `getBoundingClientRect` y redibujar en `resize`.
- Pruebas ampliadas en `tests/test_diagnostico_flexo.py` y `tests/test_resultado_flexo_template.py` cubriendo límites y escalado UI.
- Creación de `tools/audit_flexo.py` con salida JSON/Markdown.

## Recomendaciones siguientes
1. Parametrizar los umbrales restantes (tramas débiles, TAC local) en `flexo_config`.
2. Unificar la estructura de advertencias (`tipo`, `descripcion`, `bbox`, `severidad`) en toda la cadena para reducir condicionales en el front-end.
3. Extender `tools/audit_flexo.py` con verificación de claves JSON y de rutas generadas (e.g., `sim_img_web`).
4. Documentar cómo sobreescribir perfiles según material/anilox en despliegues multi-planta.

## Checklist
- [x] Se centralizaron umbrales de texto, trazo, TAC y sangrado.
- [x] Se corrigió el escalado de bounding boxes en la UI web.
- [x] Se añadieron pruebas para límites críticos (texto/trazo) y para el template.
- [x] Se creó el script `tools/audit_flexo.py` con salidas JSON/Markdown.
- [x] Se generó el presente informe.
