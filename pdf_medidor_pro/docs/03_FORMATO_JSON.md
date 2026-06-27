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
