# Kernel geométrico V2 del Editor Offset Visual

## 1. Objetivo

`editor_offset_v2/domain/geometry.py` es la fuente única de verdad geométrica para el Editor Offset Visual V2.

El kernel es puro, determinista e independiente de:

* Flask;
* DOM o navegador;
* SVG o píxeles;
* archivos PDF;
* almacenamiento de jobs;
* motores de imposición;
* preview;
* salida productiva.

Las futuras capas de canvas, selección, drag, resize, snap, preflight, CTP y output deberán consumir esta semántica. No deben volver a implementar estas fórmulas de manera independiente.

## 2. Alcance de la Fase 2

Esta fase implementa únicamente:

* modelos geométricos inmutables;
* validación numérica;
* rotaciones cardinales;
* tamaños trim y productivos;
* polígonos y bounds;
* traslación y rotación de puntos;
* contención en pliego;
* colisiones mediante Separating Axis Theorem;
* distancias entre bounds;
* fixtures independientes de Python;
* tests unitarios.

No crea rutas, frontend, TypeScript, canvas, endpoints, conexión con Repeat ni conexión con la salida productiva.

## 3. Sistema de coordenadas

El sistema coincide con Layout V2:

* unidad: milímetros;
* origen: esquina inferior izquierda del pliego;
* X positivo: derecha;
* Y positivo: arriba;
* rotación positiva: antihoraria;
* pivote: centro trim.

El kernel no contiene conversiones a coordenadas del navegador. La futura capa SVG deberá transformar el eje Y únicamente en su frontera visual.

## 4. Centro trim

La posición persistida:

```text
geometry.position_mm.x_mm
geometry.position_mm.y_mm
```

se convierte en `Point` y representa siempre el centro trim.

El centro no cambia al aplicar rotación o bleed.

## 5. Dimensiones antes de rotación

`Size` representa dimensiones estrictamente positivas.

`SlotGeometry.trim_size` conserva siempre las dimensiones trim originales, antes de rotación.

Ejemplo:

```text
trim_size = Size(90, 50)
rotation_deg = 90
oriented_size = Size(50, 90)
```

La función `oriented_size()` devuelve una medida derivada. Nunca modifica ni intercambia las dimensiones persistidas.

## 6. Rotaciones cardinales

La API pública del kernel acepta exclusivamente:

```text
0
90
180
270
```

No normaliza valores. Por tanto, rechaza:

```text
-90
89
91
360
450
NaN
infinito
booleanos
```

Las operaciones cardinales se calculan sin trigonometría para mantener resultados deterministas:

```text
0°:   (x, y)
90°:  (-y, x)
180°: (-x, -y)
270°: (y, -x)
```

## 7. Alineación con el contrato Layout V2

`CARDINAL_ROTATIONS_DEG`, definido en `layout_v2.py`, es la fuente canónica Python y se reutiliza desde el validador semántico y el kernel geométrico.

El JSON Schema refleja la misma enumeración explícita y los tests comprueban su paridad con la constante Python.

Los campos restringidos son:

* `works[].allowed_rotations_deg`;
* `slots[].geometry.rotation_deg`;
* `slots[].content_transform.rotation_deg`;
* la rotación intrínseca declarada para páginas PDF.

La rotación geométrica del slot cambia la orientación de la caja trim y del footprint productivo. La rotación interna del contenido transforma la página PDF dentro del slot y no cambia su footprint. Aunque representan operaciones distintas, ambas se limitan inicialmente a `0`, `90`, `180` o `270` porque el adaptador de salida todavía no soporta rotaciones libres del contenido.

No se habilita ni se normaliza una segunda fórmula para rotaciones arbitrarias.

## 8. Trim y bleed

La caja trim usa `trim_size` sin modificaciones.

El bleed es uniforme y no negativo. `productive_size()` calcula:

```text
productive_width  = trim_width  + 2 × bleed
productive_height = trim_height + 2 × bleed
```

El bleed no se incorpora a las dimensiones trim almacenadas.

## 9. Footprint

El footprint es información derivada y no se persiste.

El kernel puede derivar:

* polígono trim;
* polígono productivo con bleed;
* bounds trim;
* bounds productivos;
* tamaño orientado.

Para rotaciones 90° y 270° el tamaño orientado intercambia ancho y alto. Para 0° y 180° los conserva.

## 10. Modelos inmutables

### `Point`

Contiene coordenadas finitas `x` e `y`.

### `Size`

Contiene `width` y `height` estrictamente positivos.

### `Bounds`

Contiene:

* `left`;
* `right`;
* `bottom`;
* `top`.

Deriva:

* `width`;
* `height`;
* `center`.

### `Polygon`

Contiene al menos tres puntos, debe ser convexo, no degenerado y antihorario.

### `SlotGeometry`

Contiene exclusivamente:

* `center`;
* `trim_size`;
* `bleed`;
* `rotation_deg`.

Todos los modelos usan `dataclass(frozen=True)`.

## 11. Orden de vértices

`rectangle_polygon()` construye primero los vértices locales en este orden:

1. inferior izquierdo;
2. inferior derecho;
3. superior derecho;
4. superior izquierdo.

Después rota esos mismos vértices alrededor del centro. El primer punto continúa representando la esquina inferior izquierda local, aunque después de rotar ya no sea la esquina inferior izquierda del bounding box global.

El orden resultante siempre es antihorario y estable.

## 12. Bounds y conversiones

`polygon_bounds()` calcula la envolvente alineada a los ejes.

Funciones específicas:

* `trim_bounds()`;
* `bleed_bounds()`;
* `center_to_trim_bounds()`;
* `center_to_bleed_bounds()`;
* `sheet_bounds()`.

La esquina inferior izquierda de una caja se obtiene como:

```text
Point(bounds.left, bounds.bottom)
```

El centro se recupera mediante `bounds.center`.

## 13. Contención

`point_in_polygon()` considera dentro:

* interior;
* borde;
* vértices.

`polygon_within_bounds()` requiere que todos los vértices estén dentro de los bounds, considerando la tolerancia numérica.

`slot_within_sheet()` utiliza por defecto el polígono productivo con bleed:

```python
slot_within_sheet(slot, sheet_size, use_bleed=True)
```

La validación trim debe solicitarse de manera explícita con `use_bleed=False`.

## 14. Colisiones

`polygons_intersect()` usa Separating Axis Theorem sobre polígonos convexos.

No determina colisiones solamente mediante bounding boxes. Esto permite rechazar falsos positivos cuando dos polígonos rotados tienen bounds cruzados pero no se intersectan.

La política de contacto es:

* solapamiento con área positiva: `True`;
* contacto únicamente por borde: `False`;
* contacto únicamente por vértice: `False`;
* penetración menor o igual a la tolerancia numérica: `False`.

`slots_overlap()` usa bleed por defecto. El caller debe pedir explícitamente `use_bleed=False` para comparar trim.

Aunque `Polygon` y SAT pueden operar con cualquier polígono convexo ya construido, las funciones públicas que generan geometría de slots no permiten rotaciones no cardinales.

## 15. Tolerancia numérica

La constante es:

```text
DEFAULT_TOLERANCE_MM = 1e-9
```

Es una tolerancia extremadamente pequeña destinada únicamente a errores de coma flotante. No representa:

* separación entre trabajos;
* margen de seguridad;
* bleed;
* distancia mínima productiva;
* tolerancia mecánica de imprenta.

La utilizan:

* comprobación de puntos sobre segmentos;
* contención de polígonos;
* comparación SAT;
* validación interna de convexidad.

Una separación productiva debe almacenarse y validarse como una magnitud explícita distinta.

## 16. Distancias

`horizontal_gap()` y `vertical_gap()` devuelven valores con signo:

* positivo: separación;
* cero: contacto;
* negativo: cantidad de solapamiento en ese eje.

`distance_between_bounds()` devuelve la distancia euclidiana mínima entre dos bounds:

* bounds separados: distancia positiva;
* contacto: cero;
* solapamiento: cero.

Para distinguir contacto de solapamiento deben consultarse los gaps con signo o SAT.

## 17. API pública

Modelos:

```text
Point
Size
Bounds
Polygon
SlotGeometry
```

Validación:

```text
is_finite_number
validate_finite
validate_positive
validate_non_negative
validate_cardinal_rotation
```

Tamaños y transformaciones:

```text
productive_size
oriented_size
rotate_point
translate_polygon
```

Polígonos y bounds:

```text
rectangle_polygon
trim_polygon
bleed_polygon
polygon_bounds
trim_bounds
bleed_bounds
center_to_trim_bounds
center_to_bleed_bounds
sheet_bounds
```

Contención y colisiones:

```text
point_in_polygon
polygon_within_bounds
slot_within_sheet
polygons_intersect
slots_overlap
```

Distancias:

```text
horizontal_gap
vertical_gap
distance_between_bounds
```

## 18. Ejemplo

```python
from editor_offset_v2.domain.geometry import (
    Point,
    Size,
    SlotGeometry,
    bleed_bounds,
    slot_within_sheet,
)

slot = SlotGeometry(
    center=Point(60, 55),
    trim_size=Size(90, 50),
    bleed=3,
    rotation_deg=90,
)

footprint = bleed_bounds(slot)
# Bounds(left=32, right=88, bottom=7, top=103)

inside = slot_within_sheet(slot, Size(700, 500))
# True
```

## 19. Invariantes

* no se aceptan booleanos como números;
* no se aceptan NaN o infinito;
* las dimensiones son positivas;
* el bleed es no negativo;
* la rotación es cardinal y no se normaliza;
* el centro trim se conserva;
* el tamaño trim persistido nunca se intercambia;
* los polígonos rectangulares son convexos y antihorarios;
* el footprint es derivado;
* el contacto de bordes no es overlap;
* las operaciones no modifican sus argumentos.

## 20. Fixtures y futura paridad TypeScript

`tests/fixtures/editor_offset_v2/geometry_cases.json` no contiene objetos Python. Usa únicamente JSON y milímetros.

Incluye:

* cuatro rotaciones cardinales;
* bleed cero y bleed de 3 mm;
* coordenadas decimales;
* límites del pliego;
* colisiones y contactos;
* overlap provocado únicamente por bleed;
* falsos positivos de bounds;
* dimensiones realistas de offset.

La futura implementación TypeScript deberá ejecutar los mismos fixtures y producir los mismos polígonos, bounds y resultados booleanos. La paridad debe comprobarse antes de conectar el canvas SVG.

## 21. No implementado todavía

Esta fase no incluye:

* conversiones a píxeles o SVG;
* viewport, zoom o pan;
* drag o resize;
* handles;
* snap y smart guides;
* alineación o distribución de grupos;
* guías y reglas;
* geometría de marcas CTP;
* parsing automático del layout completo;
* preflight productivo;
* adaptación a `montaje_offset_inteligente.py`;
* TypeScript;
* rotaciones arbitrarias.

Las futuras capas deben importar el kernel o validar paridad contra sus fixtures. No deben copiar estas fórmulas a módulos independientes.
