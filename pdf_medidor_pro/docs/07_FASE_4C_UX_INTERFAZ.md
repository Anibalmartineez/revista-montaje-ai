# 07 - Fase 4C UX e Interfaz

## Objetivo

Fase 4C limpia duplicaciones visuales y corrige el pan temporal con barra espaciadora sin agregar herramientas nuevas ni cambiar contratos.

## Distribucion

- Barra superior: acciones globales, undo/redo, export JSON/PNG y zoom.
- Panel izquierdo: herramientas y opciones de herramienta.
- Panel derecho: inspector del PDF u objeto seleccionado, medidas automaticas y JSON tecnico.
- Barra inferior: herramienta activa, zoom, pagina y coordenadas del mouse.

## Herramientas

Las herramientas visibles viven solo en el panel izquierdo:

- Seleccionar;
- Mano;
- Linea;
- Rectangulo;
- Calibracion;
- Guias.

El controlador sigue usando `data-pmp-tool` como mecanismo unico de seleccion de herramienta.

## Atajos

- `H`: Mano.
- `L`: Linea.
- `R`: Rectangulo.
- `C`: Calibracion.
- `G`: Guias.
- `V` o `S`: Seleccionar.

## Pan con espacio

`Espacio + arrastrar` activa pan temporal y mueve el visor en X e Y. No modifica mediciones, no registra undo/redo y no interfiere con nudging de flechas.

## Informacion automatica

MediaBox, CropBox, TrimBox, BleedBox, ArtBox, pagina y render se muestran solo en el inspector derecho cuando no hay objeto seleccionado.
