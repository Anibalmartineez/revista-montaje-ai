# Fase 36 — Endurecimiento operativo de salida V2

## Objetivo

Comprobar que la salida V2 se comporta de forma repetible bajo regeneración,
varias páginas, cantidades altas y fallos de escritura, conservando la
separación entre diagnóstico, layout y artefactos derivados.

## Cobertura incorporada

- Repeat y el planificador multipágina conservan las cuatro orientaciones
  cardinales por página.
- La suite de frontend mantiene una prueba determinista con 500 slots.
- El inspector PDF valida documentos de varias páginas, límites de páginas,
  cajas ausentes y miniaturas acotadas.
- Preview y PDF final se regeneran sobre el mismo nombre de revisión; el
  resultado binario es determinista y no deja temporales.
- Preview publica mediante archivo temporal, `fsync` y `os.replace`; un fallo
  de publicación limpia el temporal y no crea un artefacto final.
- El repositorio conserva escritura atómica, compare-and-swap y rechazo de
  reportes de preflight obsoletos.
- Playwright V2 ejercita desde la interfaz la creación de job, carga, Repeat,
  aplicación, undo/redo, guardado y recarga.

## Evidencia ejecutada

- 122 pruebas Node V2.
- 437 pruebas Python V2, con 1 caso omitido por el fixture existente.
- 22 pruebas Playwright V2.
- Pruebas focalizadas de regeneración y fallo de publicación: 17 Python.

Las advertencias corresponden a dependencias de terceros (PyPDF2,
PyMuPDF/matplotlib) y no a fallos de la aplicación.

## Límites restantes

La concurrencia de procesos múltiples y la retención/limpieza automática de
artefactos requieren una prueba de carga operativa separada. CTP y la salida
vectorial final siguen bloqueados hasta cerrar fixtures y contrato de
preflight; este endurecimiento no los habilita.
