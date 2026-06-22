# Clientes

Fase 9.2 agrega gestion aislada de clientes dentro de `sistema_presupuesto/`.

No registra el Blueprint en la app principal, no integra con Editor Offset Visual y no conecta clientes con presupuestos todavia.

## Persistencia

Cada cliente se guarda como un JSON individual bajo:

```text
data/clientes/<cliente_id>.json
```

La carpeta se conserva con:

```text
data/clientes/.gitkeep
```

El repositorio responsable es:

```text
backend/client_repository.py
```

## Estructura

```json
{
  "cliente_id": "cli_20260622_abcd1234abcd",
  "nombre": "Cliente ejemplo",
  "empresa": "",
  "telefono": "",
  "email": "",
  "ruc": "",
  "notas": "",
  "created_at": "2026-06-22T12:00:00Z",
  "updated_at": "2026-06-22T12:00:00Z"
}
```

## Reglas

- `cliente_id` es tecnico e interno.
- `cliente_id` lo genera el backend.
- `nombre` es obligatorio.
- `empresa` es opcional.
- `telefono` es opcional.
- `email` es opcional.
- si `email` existe, debe tener formato basico valido.
- `ruc` es opcional.
- `notas` es opcional.
- `created_at` y `updated_at` los genera el backend.
- no se confia en IDs ni fechas enviados por frontend.
- no se permiten rutas absolutas ni path traversal.

## Endpoints aislados

Base:

```text
/api/sistema-presupuesto
```

Listar clientes:

```text
GET /clientes
```

Crear cliente:

```text
POST /clientes
```

Ver cliente:

```text
GET /clientes/<cliente_id>
```

Actualizar cliente:

```text
PUT /clientes/<cliente_id>
```

Eliminar cliente:

```text
DELETE /clientes/<cliente_id>
```

## UI aislada

La UI de desarrollo agrega una seccion `Clientes`.

Permite:

- listar clientes;
- crear cliente;
- editar cliente;
- eliminar cliente;
- mostrar errores de validacion devueltos por backend.

## Limitaciones

- No hay autenticacion ni usuarios.
- No hay deduplicacion avanzada.
- No hay busqueda avanzada.
- No hay historial de cambios de clientes.
- No hay numeracion comercial.
- No hay PDF comercial.
- No se asocian clientes a presupuestos todavia.
- No se integra con Editor Offset Visual.

## Seguridad operativa

Clientes es una capa comercial aislada.

El backend valida y persiste los datos. La UI solo envia campos editables y muestra respuestas.
