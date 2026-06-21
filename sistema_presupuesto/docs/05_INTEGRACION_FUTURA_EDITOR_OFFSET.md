# Integracion Futura con Editor Offset Visual

Este documento define el enfoque futuro de integracion entre `sistema_presupuesto/` y el Editor Offset Visual.

En Fase 1 no se implementa ninguna integracion.

## Regla central

La integracion futura debe ser por adaptador read-only.

El Sistema Presupuesto no debe:

- modificar `layout_constructor.json`;
- escribir en `static/constructor_offset_jobs/`;
- tocar rutas del Editor;
- tocar templates del Editor;
- tocar JavaScript del Editor;
- tocar CSS del Editor;
- tocar motores de imposicion;
- tocar preview o PDF final;
- tocar `montaje_offset_inteligente.py`.

## Datos que el Editor podria aportar en el futuro

Datos potenciales del montaje:

- formato de pliego desde `sheet_mm`;
- margenes y area util;
- CTP activo y pinza;
- caras usadas: `front` y `back`;
- repeticiones reales por pliego;
- slots por `design_ref`;
- sangrado efectivo;
- marcas de corte;
- motor de imposicion usado;
- cantidad de formas solicitadas;
- advertencias sobre PDF faltante o datos ambiguos.

Datos que probablemente deben venir del presupuesto, no del Editor:

- cantidad de ejemplares;
- cliente;
- precio de papel;
- maquina;
- costos por hora;
- terminaciones;
- impuestos;
- margen o markup;
- condiciones comerciales.

## Riesgos conocidos

- La semantica de `design.width_mm` y `design.height_mm` puede ser trim, media box o caja con bleed.
- El doble cara puede duplicar repeticiones si se suma frente y dorso sin criterio.
- `nesting` e `hybrid` pueden no tener la misma caracterizacion que `repeat`.
- Preview y PDF final no son necesariamente equivalentes.
- Un PDF referenciado puede faltar fisicamente aunque el contrato estructural sea valido.

## Contrato snapshot futuro

Contrato conceptual, no implementado:

```json
{
  "schema": "editor_offset_visual_to_presupuesto",
  "schema_version": 1,
  "source": {
    "system": "editor_offset_visual",
    "job_id": "string",
    "layout_contract_version": null
  },
  "sheet": {
    "sheet_mm": [640, 880],
    "margins_mm": [10, 10, 10, 10],
    "usable_area_mm": [620, 860],
    "usable_area_m2": "0.5332",
    "ctp_enabled": true,
    "gripper_mm": 10
  },
  "production": {
    "faces": ["front", "back"],
    "crop_marks": true,
    "bleed_mm": 3,
    "imposition_engine": "repeat",
    "estimated_waste_pct": null
  },
  "items": [
    {
      "design_ref": "file0",
      "work_id": null,
      "filename": "pieza.pdf",
      "final_size_mm": [100, 50],
      "size_semantics": "pending_trim_vs_media_vs_bleed_box",
      "pages": null,
      "copies": null,
      "colors": {
        "front": 4,
        "back": 0,
        "as_string": "4/0"
      },
      "bleed_mm": 3,
      "forms_requested": 15,
      "forms_on_sheet_front": 15,
      "forms_on_sheet_back": 0,
      "budget_forms_per_sheet": 15,
      "slots": {
        "front": 15,
        "back": 0,
        "total": 15
      }
    }
  ],
  "warnings": []
}
```

## Plan futuro de integracion

1. Crear adaptador puro `build_presupuesto_snapshot_from_layout(layout)`.
2. Probarlo con fixtures de layouts, no con jobs reales al inicio.
3. Versionar el contrato snapshot.
4. Importar el snapshot desde presupuesto como dato externo.
5. Mantener escritura del Editor y escritura de presupuesto completamente separadas.

## Estado actual

No implementado.

Este documento existe solo para dejar preparado el contrato conceptual y las reglas de seguridad.
