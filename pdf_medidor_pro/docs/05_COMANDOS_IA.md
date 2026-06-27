# 05 - Comandos IA

## Comandos soportados

- `medi esta etiqueta`
- `mide esta etiqueta`
- `conta cuantas etiquetas hay`
- `contar etiquetas`
- `medi la separacion`
- `detectar area impresa`
- `buscar sangrado`

## Comportamiento

Los comandos que requieren contexto dejan al visor esperando un clic.

Ejemplo:

```text
medi esta etiqueta
```

Respuesta esperada:

```text
Ahora hace clic sobre el objeto.
```

## Limitaciones

- La deteccion se basa en pixeles no blancos del preview.
- No interpreta semantica real del PDF.
- Objetos conectados por lineas o fondos oscuros pueden unirse.
- El conteo puede subestimar o sobreestimar piezas si hay textos, marcas o ruido.
