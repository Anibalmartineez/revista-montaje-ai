# Shell, Blueprint y repositorio de jobs del Editor Offset Visual V2

## 1. Objetivo de la Fase 4

La Fase 4 crea la primera superficie HTTP accesible del Editor Offset Visual V2
y su persistencia aislada. Permite activar el módulo, crear jobs, abrirlos,
leer Layout V2 y guardar mediante revisión optimista.

Esta fase no conecta canvas, herramientas, assets, upload, Repeat, adaptador de
salida, preview, PDF ni CTP productivo.

```text
/editor_offset_visual_v2
        -> Blueprint V2
        -> JobService
        -> JobRepository
        -> instance/editor_offset_v2_jobs/<job_id>/layout_v2.json
```

El Editor V1 mantiene sus rutas, scripts, servicios y almacenamiento sin
cambios.

## 2. Registro del Blueprint

El blueprint está definido en:

```text
editor_offset_v2/blueprint.py
```

`app.py` realiza una única integración explícita:

```python
from editor_offset_v2.blueprint import init_editor_offset_v2

app.register_blueprint(routes_bp)
init_editor_offset_v2(app)
```

`init_editor_offset_v2()` instala los defaults de configuración y registra el
blueprint solo si su nombre todavía no está presente. Las rutas no se agregan a
`routes.py` y no se importan servicios V1.

El repositorio y el servicio se construyen desde la configuración de la app que
atiende cada request. No existe una ruta global ligada a una carpeta de
desarrollo.

## 3. Feature flag

La configuración canónica es:

```text
EDITOR_OFFSET_V2_ENABLED
```

El valor por defecto es `false`. Puede habilitarse mediante configuración Flask
o variable de entorno con `1`, `true`, `yes`, `y` u `on`.

Comportamiento desactivado:

- las páginas V2 responden `404`;
- las API V2 responden `404` con código estructurado `V2_DISABLED`;
- las rutas V1 continúan funcionando;
- el dominio V2 no conoce el feature flag.

Los tests establecen la bandera por instancia de Flask, de modo que activar una
app de prueba no cambia otra app ni una variable global permanente.

## 4. Rutas

Interfaz:

```text
GET /editor_offset_visual_v2
GET /editor_offset_visual_v2/<job_id>
```

API:

```text
POST /api/editor-offset-v2/jobs
GET  /api/editor-offset-v2/jobs/<job_id>
PUT  /api/editor-offset-v2/jobs/<job_id>/layout
```

No se agregó endpoint de health porque el propio `404 V2_DISABLED` y la ruta
shell son suficientes para comprobar el estado de la función.

## 5. Configuración del almacenamiento

La clave configurable es:

```text
EDITOR_OFFSET_V2_JOBS_ROOT
```

Su default es:

```text
<Flask instance_path>/editor_offset_v2_jobs
```

Por job se crea:

```text
instance/editor_offset_v2_jobs/<job_id>/
├── layout_v2.json
├── assets/
├── derived/
├── previews/
├── outputs/
└── reports/
```

La carpeta generada está ignorada específicamente por Git. El repositorio no
consulta ni escribe `static/constructor_offset_jobs/`.

## 6. IDs de job

El servidor genera 12 bytes aleatorios criptográficos y los representa como 24
caracteres hexadecimales:

```text
ev2_<24 caracteres hexadecimales>
```

Ejemplo:

```text
ev2_0123456789abcdef01234567
```

El cliente no puede elegir `job_id`. El repositorio valida el patrón completo y
una longitud máxima antes de resolver cualquier path.

Se rechazan:

- `..`;
- `/` y `\`;
- rutas absolutas Windows y POSIX;
- drives;
- mayúsculas;
- caracteres fuera de hexadecimal;
- IDs cortos, largos o con otro prefijo.

La ruta final se resuelve y se comprueba nuevamente contra la raíz configurada.

## 7. Layout inicial

`create_initial_layout_v2()` construye el documento en código de aplicación. No
lee ni copia fixtures durante la ejecución.

Defaults iniciales:

- `layout_schema_version = 2`;
- revisión inicial `1`;
- timestamps UTC con sufijo `Z`;
- pliego `700 x 500 mm`;
- márgenes imprimibles en cero;
- solo cara frontal;
- modo dúplex desactivado;
- `assets`, `works` y `slots` vacíos;
- motor manual sin resultado previo;
- exportación vector hybrid a 300 dpi;
- perfil de marcas con crop marks y marcas avanzadas desactivadas;
- CTP desactivado.

El contrato actual admite correctamente colecciones vacías para un job nuevo;
no fue necesario modificar Layout V2, el JSON Schema ni el validador.

Antes de devolverse, el layout inicial se comprueba con
`validate_layout_v2()`.

## 8. Creación

Request:

```http
POST /api/editor-offset-v2/jobs
Content-Type: application/json

{
  "name": "Catálogo agosto"
}
```

`name` es opcional. No se aceptan otros campos.

Respuesta `201`:

```json
{
  "ok": true,
  "job_id": "ev2_0123456789abcdef01234567",
  "revision": 1,
  "open_url": "/editor_offset_visual_v2/ev2_0123456789abcdef01234567",
  "layout": {
    "layout_schema_version": 2
  }
}
```

La respuesta real contiene el Layout V2 inicial completo. No contiene la ruta
física de la carpeta del job.

## 9. Lectura

Request:

```http
GET /api/editor-offset-v2/jobs/ev2_0123456789abcdef01234567
```

La lectura:

1. valida el ID;
2. exige que exista el directorio;
3. exige `layout_v2.json`;
4. decodifica UTF-8 y JSON estricto;
5. rechaza `NaN` e infinitos;
6. valida todo el contrato Layout V2;
7. confirma que `layout.job.id` coincida con el directorio.

Un job inexistente devuelve `JOB_NOT_FOUND`. JSON corrupto o archivo ausente se
reporta como `PERSISTENCE_ERROR`. Un documento persistido que no sea V2 se
reporta como `INVALID_LAYOUT`. No se exponen stack traces en la API.

## 10. Guardado y control de revisión

Request:

```http
PUT /api/editor-offset-v2/jobs/ev2_0123456789abcdef01234567/layout
Content-Type: application/json

{
  "base_revision": 1,
  "layout": {
    "layout_schema_version": 2,
    "job": {
      "id": "ev2_0123456789abcdef01234567",
      "revision": 1
    }
  }
}
```

El ejemplo abreviado debe sustituirse por el Layout V2 completo.

Reglas:

1. el job debe existir;
2. `base_revision` debe ser un entero no negativo;
3. debe coincidir con la revisión persistida;
4. `layout.job.id` debe coincidir con la URL;
5. `layout.job.revision` debe coincidir con `base_revision`;
6. el layout recibido debe ser V2 válido;
7. el servidor conserva `created_at` persistido;
8. el servidor incrementa la revisión;
9. el servidor actualiza `updated_at` en UTC;
10. se valida nuevamente el documento final;
11. el repositorio realiza un compare-and-swap antes del reemplazo.

Una diferencia devuelve `409 REVISION_CONFLICT`. No existe merge automático ni
sobrescritura silenciosa.

El compare-and-swap usa un lock por job dentro del proceso Flask. Esto evita que
dos requests del mismo proceso superen simultáneamente la comprobación. Para un
despliegue futuro con múltiples procesos será necesario incorporar un lock de
archivo o almacenamiento transaccional compartido.

## 11. Escritura atómica

`JobRepository` nunca escribe directamente sobre `layout_v2.json`.

Proceso:

1. crea un temporal oculto dentro del mismo directorio del job;
2. serializa UTF-8 con `ensure_ascii=false`;
3. usa indentación de dos espacios y claves ordenadas;
4. utiliza `allow_nan=false`;
5. agrega nueva línea final;
6. ejecuta `flush()` y `fsync()`;
7. cierra el archivo;
8. reemplaza el destino con `os.replace()`;
9. elimina el temporal ante un error controlado.

Al estar origen y destino en el mismo directorio, `os.replace()` utiliza la
operación atómica disponible en el sistema. Si el reemplazo falla, el layout
anterior permanece intacto.

## 12. Errores estructurados

La capa de aplicación utiliza:

```text
JOB_NOT_FOUND
INVALID_JOB_ID
INVALID_LAYOUT
REVISION_CONFLICT
PERSISTENCE_ERROR
V2_DISABLED
```

Formato HTTP:

```json
{
  "ok": false,
  "error": {
    "code": "REVISION_CONFLICT",
    "message": "The submitted base revision does not match the persisted layout"
  }
}
```

Para layouts inválidos puede incluirse `error.issues` con código, path y
mensaje del validador canónico.

## 13. Template shell

El shell vive en:

```text
templates/editor_offset_visual_v2.html
```

Contiene únicamente:

- barra superior e identidad del documento;
- botón funcional `Nuevo job`;
- región reservada para herramientas;
- panel reservado para assets;
- superficie reservada para canvas;
- inspector básico;
- barra inferior de estado;
- job, revisión y estado `Shell V2`.

Carga solamente:

```text
static/css/editor_offset_visual_v2.css
static/js/editor_offset_visual_v2.js
```

No carga scripts V1, las nueve pestañas, store, canvas SVG, undo/redo ni
controles productivos falsos. El JavaScript únicamente lee el contexto JSON,
crea un job y abre su URL.

## 14. Seguridad e invariantes

- La raíz se suministra por configuración Flask o parámetro del repositorio.
- Ninguna ruta física se recibe desde el cliente.
- Los jobs no viven en `static/`.
- Los IDs se validan antes de tocar el filesystem.
- Layout V1 y campos legacy son rechazados por el validador V2.
- JSON no finito no puede leerse ni escribirse.
- Un error previo al reemplazo no modifica el layout persistido.
- El cliente no controla la revisión nueva.
- El feature flag pertenece a Flask, no al dominio.
- El blueprint no conoce detalles de escritura atómica.
- El repositorio no contiene lógica HTTP.

## 15. Fuera de alcance

Esta fase no implementa:

- canvas funcional;
- store frontend;
- assets o upload;
- Repeat u otros motores;
- output adapter;
- preflight productivo;
- preview o PDF;
- CTP productivo;
- autosave;
- undo/redo;
- TypeScript o Vite;
- migración de jobs V1.

## 16. Próxima fase

La próxima fase puede incorporar el store central y el canvas SVG sobre esta
frontera. Deberá cargar el contexto del job, conservar `base_revision`, mantener
dirty state y utilizar el endpoint PUT sin duplicar validación ni persistencia
en JavaScript.
