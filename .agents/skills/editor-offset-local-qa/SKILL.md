---
name: editor-offset-local-qa
description: Iniciar, comprobar y detener de forma controlada Flask local para Editor Offset Visual V1, V2 o ambos, y preparar pruebas interactivas. Usar para verificar rutas, habilitar V2 con flags de proceso, evitar servidores duplicados, diagnosticar el arranque o detener únicamente el proceso registrado por esta Skill.
---

# Editor Offset Local QA

## Selección de versión

- Usar v1 para /editor_offset_visual.
- Usar v2 para /editor_offset_visual_v2.
- Usar both cuando ambas superficies deban responder en el mismo proceso.
- Si el usuario menciona V2, su URL, Layout V2 o editor_offset_v2, seleccionar v2.
- Si no indica versión y el contexto no la determina, conservar v1 para compatibilidad.
- Mantener las herramientas de desarrollo V2 desactivadas. Usar -EnableV2DevTools únicamente cuando el usuario lo solicite expresamente.

Para v2 y both, el proceso hijo recibe:

    EDITOR_OFFSET_V2_ENABLED=1
    EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED=0

El script usa directamente el Python del venv. No activa el entorno virtual ni deja variables persistentes en la terminal del usuario.

## Reglas de seguridad

- Trabajar siempre desde la raíz Git del repositorio activo. Ejecutar primero `git rev-parse --show-toplevel` y usar la ruta devuelta como directorio de trabajo.
- Verificar que existan `venv\Scripts\python.exe` y `app.py` en esa raíz.
- Usar directamente `venv\Scripts\python.exe`; no depender de activar manualmente el entorno virtual ni de una terminal que ya lo tenga activado.
- Usar rutas relativas a la raíz cuando sea posible.
- No modificar código, dependencias, variables persistentes, configuración ni archivos de la aplicación.
- Esta Skill administra Flask y comprueba HTTP. La exploración visual posterior debe usar la herramienta de navegador autorizada para la tarea.
- No afirmar que una página funciona si no fue comprobada realmente. No continuar con pruebas visuales si Flask no responde correctamente.
- Si otro servidor ya responde en el puerto 5000 pero no sirve la versión pedida, no iniciar otro proceso. Informar que debe detenerse o reiniciarse con el target correcto.

## Flujo obligatorio

1. Confirmar la raíz con `git rev-parse --show-toplevel`.
2. Verificar `venv\Scripts\python.exe`.
3. Seleccionar `v1`, `v2` o `both` según la solicitud.
4. Ejecutar `venv\Scripts\python.exe .agents\skills\editor-offset-local-qa\scripts\check_flask.py --target <target>`.
5. Si todas las rutas obligatorias responden, informar el resultado y no iniciar un segundo servidor.
6. Si no responden, ejecutar `powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\start_flask.ps1 -Target <target>`.
7. Volver a ejecutar `check_flask.py --target <target>`. Informar URLs, target, flags V2, intentos, estados HTTP y criterio de éxito realmente comprobados.
8. Si Flask falla, leer y resumir los archivos de stdout y stderr informados por el script de inicio. No ocultar errores ni continuar con pruebas visuales.
9. Cuando el usuario solicite detener el servidor, ejecutar `powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\stop_flask.ps1` y reportar la verificación y el resultado reales.

Comandos de referencia para V2:

    venv\Scripts\python.exe .agents\skills\editor-offset-local-qa\scripts\check_flask.py --target v2
    powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\start_flask.ps1 -Target v2
    venv\Scripts\python.exe .agents\skills\editor-offset-local-qa\scripts\check_flask.py --target v2

URL esperada:

    http://127.0.0.1:5000/editor_offset_visual_v2

## Gestión del proceso

- Guardar PID, stdout, stderr y metadatos dentro de `.codex-runtime\editor-offset-local-qa\`, creada solamente al ejecutar el inicio.
- Comprobar primero si Flask ya responde y no iniciar otro servidor si está activo.
- No crear procesos duplicados cuando exista un PID guardado todavía activo.
- Registrar en `process.json` el target y los valores efectivos de los flags V2.
- Aplicar los flags V2 únicamente al proceso hijo controlado; no cambiar variables de usuario o máquina.
- Detener únicamente el PID guardado por esta Skill y verificar razonablemente su ejecutable, ruta, hora de inicio y línea de comandos mediante los metadatos.
- No finalizar procesos desconocidos, no matar procesos por puerto y no usar comandos generales como `taskkill /IM python.exe`.
- Si la verificación del proceso no es suficiente, no detenerlo y explicar la razón.
- Conservar los logs de ejecuciones anteriores. Los nuevos logs usan nombres con marca temporal para evitar sobrescrituras; no borrar logs salvo necesidad comprobada y, en ese caso, preservarlos o rotarlos.

## Invocación desde un chat nuevo

Ejemplos:

- `Usa $editor-offset-local-qa para comprobar e iniciar Flask con Editor V2.`
- `Usa $editor-offset-local-qa para comprobar V1 y V2.`
- `Usa $editor-offset-local-qa para detener el Flask iniciado por la Skill.`

Indicar si solo se desea comprobar, iniciar si hace falta o detener.

