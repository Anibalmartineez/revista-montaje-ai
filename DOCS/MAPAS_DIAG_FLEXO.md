# Mapas de llamadas y dependencias – Diagnóstico Flexo

## 1. Call graphs principales

### `routes.py::revision`
```mermaid
graph TD
  A[POST /revision] --> B[validar formulario]
  B --> C[guardar PDF temporal]
  C --> D[revisar_diseño_flexo]
  D --> D1[calcular_metricas_cobertura]
  D --> D2[analizar_advertencias_disenio]
  D --> D3[detectar_tramas_débiles]
  D --> D4[detectar_overprints]
  D --> D5[generar_reporte_tecnico]
  D --> D6[simular_riesgos]
  C --> E[analizar_riesgos_pdf]
  C --> F[generar_preview_diagnostico]
  B --> G[inyectar_parametros_simulacion]
  G --> H[resultado_data → render]
```

### `montaje_flexo.py::revisar_diseño_flexo`
```mermaid
graph TD
  R0[revisar_diseño_flexo] --> R1[calcular_metricas_cobertura]
  R0 --> R2[verificar_dimensiones]
  R0 --> R3[analizar_advertencias_disenio]
  R3 --> R3a[verificar_textos_pequenos]
  R3 --> R3b[verificar_lineas_finas_v2]
  R3 --> R3c[verificar_modo_color]
  R3 --> R3d[revisar_sangrado]
  R0 --> R4[verificar_resolucion_imagenes]
  R0 --> R5[detectar_capas_especiales]
  R0 --> R6[analizar_contraste]
  R0 --> R7[detectar_tramas_débiles]
  R7 --> R7a[detectar_trama_debil_negro]
  R0 --> R8[detectar_overprints]
  R0 --> R9[detectar_tintas_pantone]
  R0 --> R10[generar_diagnostico_texto]
  R0 --> R11[generar_reporte_tecnico]
  R0 --> R12[simular_riesgos]
```

### `diagnostico_flexo.py::generar_preview_diagnostico`
```mermaid
graph TD
  P0[generar_preview_diagnostico] --> P1[fitz.open]
  P1 --> P2[get_pixmap]
  P2 --> P3[guardar PNG base]
  P0 --> P4[Image.open]
  P4 --> P5[ImageDraw.rectangle]
  P0 --> P6[consolidar_advertencias]
  P6 --> P7[escalar bbox a px]
  P7 --> P8[lista advertencias_iconos]
  P3 --> P9[ruta relativa static/previews]
```

### `simulador_riesgos.py::simular_riesgos`
```mermaid
graph TD
  S0[simular_riesgos] --> S1[_a_texto]
  S0 --> S2[get_flexo_thresholds]
  S0 --> S3[regex textos]
  S0 --> S4[regex trazos]
  S0 --> S5[regex resolución]
  S0 --> S6[regex overprint/RGB]
  S0 --> S7[regex TAC]
  S0 --> S8[regex borde/sangrado]
  S0 --> S9[render filas HTML]
```

### `static/js/flexo_simulation.js`
```mermaid
graph TD
  J0[DOMContentLoaded] --> J1[setup canvas/inputs]
  J1 --> J2[applyInitialValues]
  J1 --> J3[resize]
  J3 --> J4[render]
  J1 --> J5[event listeners sliders]
  J5 --> J4
  J1 --> J6[handleExport]
  J6 --> J7[fetch /simulacion/exportar]
  J4 --> J8[actualizar métricas UI]
  J4 --> J9[dibujar patrón]
```

## 2. Dependencias entre archivos

```mermaid
graph TD
  routes.py --> montaje_flexo.py
  routes.py --> diagnostico_flexo.py
  routes.py --> advertencias_disenio.py
  routes.py --> simulador_riesgos.py
  routes.py --> preview_tecnico.py
  routes.py --> reporte_tecnico.py
  routes.py --> flexo_config.py
  montaje_flexo.py --> diagnostico_flexo.py
  montaje_flexo.py --> advertencias_disenio.py
  montaje_flexo.py --> simulador_riesgos.py
  montaje_flexo.py --> cobertura_utils.py
  montaje_flexo.py --> reporte_tecnico.py
  montaje_flexo.py --> utils.py
  advertencias_disenio.py --> flexo_config.py
  advertencias_disenio.py --> diagnostico_flexo.py
  simulador_riesgos.py --> flexo_config.py
  preview_tecnico.py --> diagnostico_flexo.py
  resultado_flexo.html --> static/js/flexo_simulation.js
  tests/test_diagnostico_flexo.py --> montaje_flexo.py
  tests/test_diagnostico_flexo.py --> advertencias_disenio.py
  tools/audit_flexo.py --> repo
```

*Las flechas indican “importa a / utiliza”.*

