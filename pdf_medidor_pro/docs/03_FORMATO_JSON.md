# 03 - Formato JSON PDF Medidor Pro

## Contrato fase 1

```json
{
  "archivo": "trabajo.pdf",
  "pagina": 1,
  "medidas_auto": {
    "mediabox_mm": {
      "ancho": 0,
      "alto": 0
    },
    "cropbox_mm": {
      "ancho": 0,
      "alto": 0
    },
    "trimbox_mm": {
      "ancho": 0,
      "alto": 0
    },
    "bleedbox_mm": {
      "ancho": 0,
      "alto": 0
    },
    "artbox_mm": {
      "ancho": 0,
      "alto": 0
    }
  },
  "medidas_manual": {
    "ancho_final_mm": 0,
    "alto_final_mm": 0
  },
  "calibracion": {
    "activa": false,
    "factor_escala": 1
  },
  "origen_medida_final": "manual",
  "confianza": "alta"
}
```

## Reglas

- `pagina` usa indice humano, empezando en `1`.
- Las medidas automaticas se expresan en milimetros.
- Si una caja no existe o no tiene dimensiones validas, se informa como `0 x 0`.
- `medidas_manual` representa el rectangulo final dibujado por el usuario.
- `calibracion.factor_escala` multiplica mediciones posteriores.
- `origen_medida_final` fase 1 puede ser `manual` o `auto`.
- `confianza` fase 1 puede ser `alta` cuando hay rectangulo manual o `media` cuando solo hay cajas automaticas.

## Ampliacion compatible Fase 3

La clave `mediciones` conserva el historial tecnico de objetos manuales:

```json
{
  "mediciones": [
    {
      "id": "r_1",
      "tipo": "rectangulo",
      "origen": "manual",
      "nombre": "Medida final",
      "visible": true,
      "color": "#2563eb",
      "stroke_width": 2,
      "pagina": 1,
      "ancho_mm": 120,
      "alto_mm": 80,
      "x_mm": 10,
      "y_mm": 15,
      "area_mm2": 9600,
      "perimetro_mm": 400,
      "angulo_deg": 0,
      "confianza": 1
    }
  ]
}
```

Reglas de compatibilidad:

- las claves base se mantienen;
- `mediciones` puede estar vacio;
- `origen` se normaliza a `manual` o `auto`;
- no existen valores de origen automatizado experimental;
- color, grosor, pagina, visibilidad y angulo describen el objeto editable.
