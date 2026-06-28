# 05 - Fase 3 Interfaz Profesional y Objetos Editables

## Objetivo

Fase 3 convierte PDF Medidor Pro en una herramienta de medicion tecnica para preprensa. El foco esta en precision, flujo de trabajo y manipulacion directa de objetos, sin agregar automatizaciones experimentales.

## Distribucion

- Barra superior: abrir PDF, guardar estado local, export JSON, export PNG, zoom y herramientas rapidas.
- Panel izquierdo: herramientas, color, grosor, unidad, decimales, medidas en vivo, snap, guias, lupa y calibracion.
- Visor central: preview PDF, reglas, centro, coordenadas, guias, canvas de medicion, lupa y snap.
- Inspector derecho: informacion PDF o propiedades del objeto seleccionado.
- Historial inferior: tabla de mediciones con acciones.

## Modelo de objetos

Las mediciones no se tratan como dibujos sueltos. Cada medicion es un objeto en milimetros:

- `linea`: puntos `a` y `b`, nombre, color, grosor, visible y pagina.
- `rectangulo`: `x_mm`, `y_mm`, `ancho_mm`, `alto_mm`, nombre, color, grosor, visible y pagina.

`static/js/object_model.js` concentra operaciones puras:

- mover;
- redimensionar rectangulo;
- renombrar;
- cambiar color;
- cambiar visibilidad;
- duplicar;
- eliminar;
- calcular metricas;
- bloquear angulo a incrementos de 45 grados.

## Interacciones

- `Seleccionar`: el clic sobre un objeto muestra manejadores y el inspector.
- `Mano`: arrastre para pan; barra espaciadora activa pan temporal.
- `Linea`: arrastre entre dos puntos; `Shift` bloquea 0, 45 y 90 grados.
- `Rectangulo`: arrastre para crear; luego puede moverse, duplicarse y redimensionarse.
- `Calibracion`: mide una linea y permite aplicar escala con una medida real.
- `Guias`: clic crea guia vertical; `Shift` clic crea guia horizontal.

Atajos:

- `H`: mano.
- `L`: linea.
- `R`: rectangulo.
- `C`: calibracion.
- `G`: guias.
- `Delete`: eliminar seleccion.
- `Ctrl`: snap estricto.
- `Shift`: bloqueo de angulo o guia horizontal.
- `Alt`: lupa temporal.

## Exportacion

El contrato JSON base no cambia. La clave `mediciones` conserva objetos manuales y sus propiedades visuales. Export PNG se realiza en el navegador y compone el preview con lineas, rectangulos, etiquetas y guias visibles.

## No objetivos

- No se agregan endpoints nuevos.
- No se agrega persistencia backend para mediciones.
- No se agregan automatizaciones experimentales.
- No se modifica la integracion principal existente.
