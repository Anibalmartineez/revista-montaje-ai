# Auditoría de diagnóstico flexo

## Resumen de hallazgos

| Severidad | Hallazgo | Archivo/Líneas |
| --- | --- | --- |
| Alta | Umbral de resolución hardcodeado (300/600 dpi) ignora `flexo_config` | `montaje_flexo.py` L258-L288 |
| Media | Cobertura “alta/baja” con límites fijos (85% / 10%) fuera de configuración oficial | `montaje_flexo.py` L645-L658 |
| Media | `detectar_capas_especiales` silencia excepciones (`except Exception: pass`) ocultando fallos en extracción de tintas | `montaje_flexo.py` L292-L330 |
| Media | `simulador_riesgos` depende de regex sobre HTML y captura sólo enteros para TAC ⇒ riesgo de falsos positivos/negativos | `simulador_riesgos.py` L55-L155 |
| Baja | Tooling actual no detecta claves JSON huérfanas (p. ej. `advertencias_total`) ni alias redundantes | `routes.py` L1432-L1463 / plantilla |
| Baja | Render doble del PDF (CMYK + RGB) en `calcular_metricas_cobertura` sin caché ⇒ costo alto en PDFs grandes | `cobertura_utils.py` L1-L46 |

_Actualización 2025-10-09:_ la duplicación de fórmulas TAC/tinta en backend/plantilla/JS quedó resuelta. `montaje_flexo.py` consolida `diagnostico_json` con métricas únicas y `resultado_flexo.html` + `flexo_simulation.js` consumen exclusivamente ese JSON (ver `tinta_utils.calcular_transmision_tinta`).

## Detalles y reproducción

### 1. Alta – Umbral de resolución hardcodeado
* **Descripción:** `verificar_resolucion_imagenes` usa `thr = 600 if is_lineart else 300`, ignorando `FlexoThresholds.min_resolution_dpi`. Cambiar el umbral en `flexo_config.py` no se propaga al chequeo principal.
* **Archivo/Líneas:** `montaje_flexo.py` L258-L288.【F:montaje_flexo.py†L258-L288】
* **Impacto:** ajustes de configuración para soportar materiales exigentes (p. ej. 400 dpi en film) no se reflejan en el diagnóstico, generando resultados incoherentes entre simulador (`simulador_riesgos`) y resumen técnico.
* **Reproducir:** setear `FlexoThresholds(min_resolution_dpi=400)` (mock en tests) y revisar que `verificar_resolucion_imagenes` siga alertando por <300 dpi.
* **Propuesta:** inyectar thresholds desde `get_flexo_thresholds(material)` y distinguir line-art con multiplicador configurable:
  ```diff
   def verificar_resolucion_imagenes(path_pdf, material: str = ""):
-     ...
-         thr = 600 if is_lineart else 300
+         thresholds = get_flexo_thresholds(material)
+         base = thresholds.min_resolution_dpi
+         thr = int(base * 2) if is_lineart else base
  ```

### 2. Media – Cobertura total fija (85% / 10%)
* **Descripción:** se consideran “muy alta” coberturas >85% y “muy baja” <10% con mensajes de riesgo fijos.【F:montaje_flexo.py†L645-L658】 No hay ajuste según material ni TAC configurado.
* **Impacto:** para materiales con TAC crítico 320% (film/cartón), 85% puede ser aceptable; en etiqueta adhesiva 10% puede seguir siendo demasiado alto.
* **Reproducir:** correr `revisar_diseño_flexo` con un PDF de cobertura 90% y configurar `FlexoThresholds.tac_warning=300` → el mensaje sigue usando 85%. Test `test_cobertura_umbral_configurable` (sugerido) evidenciaría el desvío.
* **Propuesta:** comparar contra `thresholds.tac_warning` / `thresholds.tac_critical` para adaptar mensajes.

### 3. Media – Silenciamiento en `detectar_capas_especiales`
* **Descripción:** el bloque que detecta tintas planas hace `except Exception: pass` cuando `detectar_tintas_pantone` falla.【F:montaje_flexo.py†L292-L330】 No queda rastro en logs ni en el informe.
* **Impacto:** errores de parsing (PDF corrupto, PyPDF2) ocultan la ausencia de barniz/white, reduciendo la confiabilidad.
* **Reproducir:** provocar excepción (PDF sin recursos) y revisar que no haya advertencias adicionales.
* **Propuesta:** registrar el error y generar advertencia “No se pudo identificar tintas planas (ver logs)”.

### 4. Media – Riesgos basados en regex sobre HTML
* **Descripción:** `simulador_riesgos` analiza HTML en minúsculas. La expresión `re.search(r"tac[^0-9]*(\d+)")` ignora valores decimales (ej. 279.5) y puede confundir números de otras secciones.【F:simulador_riesgos.py†L55-L155】
* **Impacto:**
  * Falsos negativos: TAC `279.5` no activa alerta aun cuando supera `tac_warning=279` (configurable).
  * Falsos positivos: cualquier texto con “tac 1000” en otro contexto dispara riesgo alto.
* **Reproducir:** `simular_riesgos("TAC 279.5%")` → devuelve “Sin riesgos” cuando debería advertir según configuración 280.
* **Propuesta:** consumir directamente `diagnostico_json['tac_total']` cuando se provee, y ampliar regex a `\d+(?:[\.,]\d+)?`.
* **Mitigación:** se implementó `USE_PIPELINE_V2` con lectura prioritaria de `tac_total_v2`/JSON y `_leer_tac` acepta decimales; la regex queda como fallback textual.

### 5. Baja – Claves JSON huérfanas / alias redundantes
* **Descripción:** el backend carga múltiples alias (`paso`, `paso_cilindro`, `paso_del_cilindro`, `cobertura_estimada`, `cobertura_base_sum`, `advertencias_total`) pero el template solo usa un subconjunto.【F:routes.py†L1432-L1463】【F:templates/resultado_flexo.html†L529-L576】
* **Impacto:** dificulta mantenimiento; cambios futuros pueden omitir actualizar alias y provocar divergencias.
* **Propuesta:** documentar claramente en README (hecho) y limpiar alias al migrar front.

### 6. Baja – Doble render sin caché en `calcular_metricas_cobertura`
* **Descripción:** la función abre el PDF y genera pixmaps CMYK y RGB cada vez.【F:cobertura_utils.py†L1-L46】 Para PDFs grandes, esto puede tardar varios segundos.
* **Impacto:** el endpoint `/revision` no cachea resultados, generando cuellos de botella si se vuelve a analizar el mismo archivo.
* **Propuesta:** cachear pixmaps temporales en disco/memoria cuando se repite el mismo PDF+dpi, o permitir inyectar pixmap precalculado desde `revisar_diseño_flexo`.

## Riesgos de falso positivo / negativo

| Regla | Riesgo | Comentario |
| --- | --- | --- |
| Resolución de imágenes | Falso positivo: imágenes line-art legítimas a 400 dpi son marcadas si se sube el umbral global a 400 sin duplicar el factor ×2 | Necesita thresholds dinámicos (Hallazgo 1). |
| TAC | Falso negativo con valores decimales y falsos positivos si la palabra “tac” aparece en contexto ajeno | Ver Hallazgo 4. |
| Trama débil | Falso positivo cuando canal K contiene ruido residual (<5%) sin bbox → advertencia genérica sin ubicación | Considerar máscara adaptativa y reporte de porcentaje afectado. |
| Sangrado | Falso negativo en diseños con múltiples páginas (solo se revisa `doc[0]`) | Extender a loop por páginas. |

## Plan de mejoras incremental

### Fase 1 – Rápidas (1-2 días)
* Parametrizar `verificar_resolucion_imagenes` con `FlexoThresholds` y exponer nuevo test (`test_resolucion_umbral_configurable`).
* Ajustar `simulador_riesgos` para consumir `diagnostico_json` cuando esté disponible y aceptar decimales.
* Agregar logging/advertencia en `detectar_capas_especiales` ante excepciones.

### Fase 2 – Intermedias (1-2 semanas)
* Unificar umbrales de cobertura/TAC usando `flexo_config` (incluir `tac_info` por material).
* Refactorizar generación de HTML de advertencias para retornar objetos estructurados (evitar regex).
* Implementar caché simple de pixmaps en `calcular_metricas_cobertura` (ej. `lru_cache` por ruta+mtime).

### Fase 3 – Valor agregado
* Extender análisis multi-página (loop PyMuPDF) con overlays segmentados y UI para seleccionar página.
* Integrar auditoría automática con CI (ejecutar `tools/audit_flexo.py` + tests y fallar ante hallazgos alta severidad).
* Crear API/JSON formal (en lugar de HTML) para que el simulador consuma métricas estructuradas (reduce riesgo de regex frágiles).

