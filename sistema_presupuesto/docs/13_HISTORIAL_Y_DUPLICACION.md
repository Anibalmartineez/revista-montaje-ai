# Historial y Duplicacion

Fase 9.5 agrega historial avanzado y duplicacion de presupuestos dentro del modulo aislado.

No registra Blueprint en la app principal, no integra con Editor Offset Visual y no toca `routes.py`.

## Historial

El listado de presupuestos guardados expone resumen operativo:

- `presupuesto_id`;
- `numero_comercial` si existe;
- `created_at`;
- producto;
- cantidad;
- precio final;
- precio unitario;
- moneda;
- estado;
- observaciones si existen.

El backend mantiene compatibilidad con presupuestos antiguos sin `numero_comercial` o sin `estado`.
Si no existe `estado`, se muestra como `borrador`.
El estado legacy `calculado` tambien se presenta como `borrador` en el historial.

## Estados

Estados permitidos:

- `borrador`;
- `enviado`;
- `aceptado`;
- `rechazado`;
- `vencido`.

Los presupuestos nuevos nacen como `borrador`.
El cambio de estado se realiza con un endpoint dedicado y no sobrescribe el presupuesto completo.

## Filtros

`GET /api/sistema-presupuesto/presupuestos` acepta:

- `q`: busca por numero comercial, producto, observaciones o `presupuesto_id`;
- `estado`: filtra por estado permitido.

El resultado se ordena por `created_at` descendente.

Ejemplos:

```text
/api/sistema-presupuesto/presupuestos?q=volante
/api/sistema-presupuesto/presupuestos?estado=enviado
```

## Duplicacion

`POST /api/sistema-presupuesto/presupuestos/<presupuesto_id>/duplicar` crea un presupuesto nuevo desde uno existente.

Reglas:

- genera nuevo `presupuesto_id`;
- genera nuevo `numero_comercial`;
- agrega `duplicado_de` con el ID original;
- fuerza estado inicial `borrador`;
- actualiza `created_at` y `updated_at`;
- copia `request` y `result` persistidos;
- no reutiliza documento PDF/HTML generado;
- no reutiliza numero comercial.

Body opcional:

```json
{
  "observaciones": "Nueva version comercial"
}
```

No se implementa patch de cantidad porque requiere recalculo y la fase 9.5 conserva duplicacion exacta.

## API aislada

```text
GET   /api/sistema-presupuesto/presupuestos
GET   /api/sistema-presupuesto/presupuestos?q=<texto>
GET   /api/sistema-presupuesto/presupuestos?estado=<estado>
PATCH /api/sistema-presupuesto/presupuestos/<presupuesto_id>/estado
POST  /api/sistema-presupuesto/presupuestos/<presupuesto_id>/duplicar
```

Cambio de estado:

```json
{
  "estado": "enviado"
}
```

Duplicacion:

```json
{
  "observaciones": "Nueva version para revisar"
}
```

## UI aislada

La UI agrega en presupuestos guardados:

- busqueda por texto;
- filtro por estado;
- visualizacion de numero comercial, estado, producto, cantidad y precios;
- selector para cambiar estado;
- boton `Duplicar`;
- campo opcional de observaciones para duplicado;
- conserva `Generar documento`.

La UI no calcula precios ni renumera presupuestos.
Todo cambio pasa por la API aislada.

## Limitaciones

- No hay integracion con app principal Flask.
- No hay integracion con Editor Offset Visual.
- No hay asociacion formal cliente-presupuesto todavia.
- No hay recalculo al duplicar con cambios de cantidad.
- No hay historial avanzado de documentos emitidos.
- No hay permisos, usuarios ni auditoria por actor.
