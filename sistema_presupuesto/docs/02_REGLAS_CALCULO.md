# Reglas de Calculo

Este documento registra reglas iniciales para el futuro motor de presupuesto offset.

No hay motor implementado en Fase 2. Los JSON creados son fixtures y contratos de diseno.

## Precision monetaria

Los calculos monetarios deben usar `Decimal`, no `float`.

Motivos:

- evitar errores binarios de punto flotante;
- controlar redondeos;
- conservar trazabilidad;
- reproducir resultados entre ejecuciones.

El redondeo debe aplicarse solo en fronteras documentadas, por ejemplo al total final o al precio unitario mostrado.

En los contratos JSON, los importes y cantidades decimales se expresan como strings para conservar precision hasta que el futuro backend los convierta a `Decimal`.

## Margen vs markup

No mezclar margen y markup.

Markup sobre costo:

```text
precio = costo * (1 + markup_pct)
```

Margen sobre precio de venta:

```text
precio = costo / (1 - margen_pct)
```

Si ambos campos vienen informados, el contrato futuro debe rechazar el payload o exigir una precedencia explicita.

En Fase 2 los fixtures usan `margen_pct` y dejan `markup_pct` en `null`.

## Papel

El costo de papel puede calcularse por pliego o por peso.

Por pliego:

```text
costo_papel = pliegos_brutos * costo_pliego
```

Por kilogramo:

```text
peso_pliego_kg = ancho_m * alto_m * gramaje_g_m2 / 1000
costo_papel = pliegos_brutos * peso_pliego_kg * costo_kg
```

Riesgos:

- usar formato de pliego incorrecto;
- ignorar compra minima;
- confundir pliego base con pliego util;
- duplicar papel en trabajos frente/dorso.

## Merma

La merma debe ser configurable.

Formula inicial:

```text
pliegos_brutos =
  ceil(pliegos_buenos + merma_arranque + (pliegos_buenos * merma_pct))
```

La merma puede depender de:

- arranque de maquina;
- largo de tirada;
- complejidad;
- cantidad de colores;
- terminaciones;
- papel dificil;
- operador o maquina.

No usar una constante unica para todos los trabajos sin documentar el supuesto.

Los fixtures iniciales usan:

- `merma_arranque_pliegos`: merma fija de arranque;
- `merma_pct`: merma porcentual de ejemplo;
- `merma_extra_pct` en procesos que pueden agregar desperdicio.

## Chapas

Formula inicial:

```text
chapas = formas_frente * colores_frente + formas_dorso * colores_dorso
```

Ejemplos:

- `4/0` en una forma: 4 chapas.
- `4/4` en una forma: 8 chapas.
- `4/1` en una forma: 5 chapas.

Tintas especiales deben sumarse como colores adicionales cuando correspondan.

## Maquina

Modelo por hora:

```text
tiempo_impresion_horas = impresiones / velocidad_pliegos_hora
costo_maquina =
  costo_arranque
  + setup_horas * costo_hora
  + tiempo_impresion_horas * costo_hora
  + lavados
```

Modelo por millar:

```text
costo_maquina = costo_arranque + (impresiones / 1000) * costo_por_millar
```

El contrato futuro debe distinguir colores, caras, pasadas y cuerpos de maquina.

Regla inicial para maquinas de varios cuerpos:

- una maquina de 4 cuerpos puede imprimir `4/0` en una pasada de frente;
- `4/4` requiere frente y dorso, por lo tanto no debe duplicar papel, pero si debe afectar chapas, pasadas y tiempo;
- una maquina de 1 cuerpo puede requerir multiples pasadas para el mismo esquema de color.

## Tinta

Modelo tecnico inicial:

```text
costo_tinta =
  area_impresa_m2
  * pliegos_brutos
  * cobertura_estimada
  * consumo_tinta_por_m2
  * costo_tinta
```

Modelo simplificado posible:

```text
costo_tinta = costo_base_tinta * colores * pliegos_brutos / 1000
```

El sistema debe registrar que modelo se uso.

En Fase 2 no se define tarifa final de tinta. Los catalogos dejan preparada la estructura de costos, pero el consumo real queda para una fase de motor.

## Terminaciones

Cada terminacion debe declarar su base de cobro:

- fijo;
- por unidad;
- por pliego;
- por hora;
- por millar;
- por metro cuadrado;
- por kilogramo.

Formula general:

```text
costo_terminacion = costo_setup + base_calculo * tarifa
```

Ejemplos:

- corte: costo fijo o por corte;
- plegado: por unidad;
- laminado: por metro cuadrado;
- engrampado: por unidad;
- troquel: setup + unidad o pliego.

## Impuestos

Los impuestos no deben estar hardcodeados.

Cada impuesto debe declarar:

- nombre;
- tasa;
- base imponible;
- moneda;
- vigencia;
- si esta incluido o no en el precio final.

Formula general:

```text
impuesto = base_imponible * tasa
```

## Precio unitario

```text
precio_unitario = precio_final / cantidad
```

Tambien conviene conservar:

```text
costo_unitario = costo_tecnico / cantidad
margen_unitario = precio_unitario - costo_unitario
```

## Orden futuro de calculo

Orden recomendado para el motor:

1. Validar contrato y catalogos.
2. Normalizar medidas y unidades.
3. Calcular tamano con sangrado.
4. Calcular o aceptar formas por pliego.
5. Calcular pliegos netos.
6. Calcular merma y pliegos brutos.
7. Calcular chapas, pasadas e impresiones.
8. Calcular papel, maquina, tinta y terminaciones.
9. Sumar costo tecnico.
10. Aplicar margen o markup.
11. Aplicar descuentos si existen.
12. Aplicar impuestos configurados.
13. Calcular precio final y precio unitario.
14. Emitir `warnings` y desglose auditable.

## Advertencias obligatorias futuras

El sistema debe advertir si:

- la pieza no entra en el pliego util;
- falta tarifa vigente;
- falta moneda;
- la cantidad es cero o negativa;
- hay margen y markup al mismo tiempo;
- se usa una imposicion manual sin validacion geometrica;
- se desconoce la semantica de medidas finales o sangrado.
