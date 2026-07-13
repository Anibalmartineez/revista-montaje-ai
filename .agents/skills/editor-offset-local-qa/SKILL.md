---
name: editor-offset-local-qa
description: Iniciar, comprobar y detener de forma controlada la aplicación Flask local de revista-montaje-ai, y preparar pruebas del Editor Offset Visual. Usar cuando Codex necesite verificar el servidor local, levantarlo sin duplicados, diagnosticar su arranque o detener únicamente el proceso registrado por esta Skill.
---

# Editor Offset Local QA

## Reglas de seguridad

- Trabajar siempre desde la raíz Git del repositorio activo. Ejecutar primero `git rev-parse --show-toplevel` y usar la ruta devuelta como directorio de trabajo.
- Verificar que existan `venv\Scripts\python.exe` y `app.py` en esa raíz.
- Usar directamente `venv\Scripts\python.exe`; no depender de activar manualmente el entorno virtual ni de una terminal que ya lo tenga activado.
- Usar rutas relativas a la raíz cuando sea posible.
- No modificar código, dependencias, variables persistentes, configuración ni archivos de la aplicación.
- En esta primera versión, no usar Chrome, Computer Use ni MCP.
- No afirmar que una página funciona si no fue comprobada realmente. No continuar con pruebas visuales si Flask no responde correctamente.

## Flujo obligatorio

1. Confirmar la raíz con `git rev-parse --show-toplevel`.
2. Verificar `venv\Scripts\python.exe`.
3. Ejecutar `venv\Scripts\python.exe .agents\skills\editor-offset-local-qa\scripts\check_flask.py`.
4. Si todas las rutas obligatorias responden, informar el resultado y no iniciar un segundo servidor.
5. Si no responden, ejecutar `powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\start_flask.ps1`.
6. Volver a ejecutar `check_flask.py`. Informar las URLs, intentos, estados HTTP y criterio de éxito realmente comprobados.
7. Si Flask falla, leer y resumir los archivos de stdout y stderr informados por el script de inicio. No ocultar errores ni continuar con pruebas visuales.
8. Cuando el usuario solicite detener el servidor, ejecutar `powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\stop_flask.ps1` y reportar la verificación y el resultado reales.

## Gestión del proceso

- Guardar PID, stdout, stderr y metadatos dentro de `.codex-runtime\editor-offset-local-qa\`, creada solamente al ejecutar el inicio.
- Comprobar primero si Flask ya responde y no iniciar otro servidor si está activo.
- No crear procesos duplicados cuando exista un PID guardado todavía activo.
- Detener únicamente el PID guardado por esta Skill y verificar razonablemente su ejecutable, ruta, hora de inicio y línea de comandos mediante los metadatos.
- No finalizar procesos desconocidos, no matar procesos por puerto y no usar comandos generales como `taskkill /IM python.exe`.
- Si la verificación del proceso no es suficiente, no detenerlo y explicar la razón.
- Conservar los logs de ejecuciones anteriores. Los nuevos logs usan nombres con marca temporal para evitar sobrescrituras; no borrar logs salvo necesidad comprobada y, en ese caso, preservarlos o rotarlos.

## Invocación desde un chat nuevo

Pedir explícitamente: `Usa $editor-offset-local-qa para comprobar e iniciar Flask localmente` o `Usa $editor-offset-local-qa para detener el Flask iniciado por la Skill`. Indicar si solo se desea comprobar, iniciar si hace falta o detener.

