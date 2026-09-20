# Editor Offset Visual V2 — nuevo punto de partida y bitácora

Fecha de apertura: 2026-09-19.

## Decisión del usuario

Continuar desde el código que ya existe, probando el editor, detectando problemas y mejorándolo en el trabajo diario. El agente conduce la investigación técnica, propone y ejecuta correcciones dentro de lo solicitado, verifica el resultado y deja registro de lo que realmente ocurrió.

Este documento inicia una nueva forma de trabajo. No establece fases, un roadmap, un orden obligatorio de defectos ni un siguiente paso predeterminado. Tampoco implica borrar o reescribir desde cero el editor existente. Las prioridades nacen del uso, de los errores reproducidos y de las necesidades que aparezcan en la sesión.

## V2 debe tener código propio e independiente

La dirección definida por el usuario es que V2 no comparta código del producto con V1 u otras superficies del repositorio. Esto incluye motores, servicios, adaptadores, reglas de negocio, frontend y persistencia. No introducir dependencias nuevas hacia módulos compartidos ni solucionar un problema V2 modificando un motor común.

Cuando una función dependa de código compartido, examinar esa dependencia y llevar la responsabilidad a una implementación propiedad de V2, con sus pruebas. Se puede aprovechar y adaptar código existente del repositorio; la versión V2 debe quedar mantenida dentro de su propia superficie y sin importar ni delegar en la implementación antigua. Un wrapper V2 alrededor de un motor compartido no acredita independencia.

Comprobar también dependencias transitivas y arranque: no afirmar independencia total por haber eliminado un único import. Las bibliotecas externas de propósito general, como Flask o las bibliotecas PDF, no son código del producto compartido con V1; esta decisión no exige reimplementarlas. La composición actual de la aplicación tampoco demuestra un arranque independiente y deberá contrastarse cuando se trabaje esa frontera.

**Estado comprobado al abrir esta bitácora:** `editor_offset_v2/infrastructure/repeat_engine_adapter.py` importa `engines.step_repeat_pro_engine` y lo utiliza. Esa dependencia contradice el objetivo de independencia y permanece sin resolver. Esta comprobación es puntual, no un inventario exhaustivo de dependencias. En esta apertura no se cambió código productivo.

## Cómo conocer el estado real

Las instrucciones actuales del usuario definen el resultado buscado. El código, el schema ejecutable, los datos y el comportamiento observado permiten determinar qué hace hoy el sistema. Las pruebas aportan evidencia dentro de su cobertura; también pueden contener expectativas obsoletas y deben revisarse cuando corresponda.

El comportamiento observado no es automáticamente correcto: un error reproducido sigue siendo un error aunque esté implementado y tenga antecedentes documentales. Evaluar los resultados contra la necesidad del operador, la integridad de sus datos y los requisitos físicos de la salida.

Los documentos anteriores siguen disponibles como referencia y memoria. No son la fuente de verdad del producto, no fijan el trabajo siguiente y no deben cargarse como lectura obligatoria para cada sesión. Consultar un antecedente concreto únicamente cuando ayude a resolver una duda actual. Sus contratos escritos describen decisiones previas que deben contrastarse con el código y la intención actual del usuario; no autorizan cambios silenciosos de formatos o geometría.

Los planes de 20, 40 y otros documentos dejan de dirigir el avance. Sus hallazgos pueden servir como pistas, pero no se heredan como una cola obligatoria ni se declaran actuales o resueltos sin comprobación. La propuesta de crear una habilidad de trazabilidad tampoco queda como tarea pendiente automática.

Este documento es la entrada al método de trabajo y a sus registros. No certifica el estado completo del editor ni reemplaza la comprobación del código.

## Trabajo diario dirigido por el agente

Partir del problema o recorrido que tenga sentido en ese momento. Probar el flujo, observar qué falla o qué dificulta trabajar y seguir la causa hasta el código responsable. Resolver decisiones técnicas rutinarias sin devolver al usuario la organización de cada paso.

Una corrección debe ser acotada y comprobable. Reproducir el problema cuando sea posible, corregirlo, comprobar el comportamiento y registrar el resultado. Para errores relevantes de geometría, persistencia o salida, conservar una regresión reproducible dentro del repositorio; no depender únicamente de archivos temporales.

Las pruebas de navegador, API, servicios y artefactos se complementan. Para un PDF, comprobar el archivo y su contenido físico/visual; un botón funcional o un HTTP 200 no demuestra una salida correcta. Al modificar una interacción, comprobar los aspectos afectados de guardado, recarga y undo/redo. La amplitud de las pruebas depende del cambio, no de una lista universal que haya que ejecutar diariamente.

Usar jobs de prueba o copias explícitas para explorar. Conservar originales, montajes del usuario y trabajo ajeno. Usar `editor-offset-local-qa` para gestionar Flask V2 cuando se necesite; las herramientas dev no arreglan la capacidad de Repeat ni sustituyen assets reales.

No exigir un plan formal ni una aprobación repetida para cada ajuste rutinario comprendido en la tarea. Si aparece una decisión de producto que no pueda inferirse, una alteración incompatible de datos o una operación destructiva, explicar la consecuencia concreta y resolver esa decisión con el usuario. Revisar el impacto inmediato no crea un roadmap.

La conducción técnica no implica trabajo programado en segundo plano ni autoriza publicación, merge, push o nuevos commits por defecto. La autorización anterior de guardar un conjunto de cambios no se extiende automáticamente a cambios futuros.

## Registro después del trabajo

Mantener aquí una bitácora breve por intervención. Documentar después de observar o cambiar; no presentar intenciones como hechos consumados. Actualizar otra referencia técnica únicamente si el cambio la afecta y resulta útil conservarla, sin sincronizar por rutina todos los documentos antiguos.

Cada entrada debe permitir entender:

- qué pidió el usuario o qué se observó;
- qué se reprodujo y en qué condiciones;
- qué cambió y en qué archivos;
- qué se verificó, con qué resultado y qué no se comprobó;
- qué quedó abierto, sin asignarle un orden obligatorio;
- el commit, si efectivamente se creó.

Usar estados explícitos: observado, reproducido, corregido y verificado, o pendiente de verificar. No dar por corregido algo porque se redactó un documento. Si una corrección se demuestra insuficiente, añadir la nueva evidencia conservando el registro anterior.

No es necesario crear un documento numerado por cada ajuste. Separar una explicación extensa solo cuando ayude a entender el trabajo, y enlazarla desde su entrada. No mantener otro mapa completo ni otro listado de prioridades en paralelo.

## Bitácora

### 2026-09-19 — Apertura del nuevo método

- **Solicitud:** trabajar día a día desde el código existente, con conducción técnica del agente, independencia de V2, pruebas y registro posterior; abandonar los planes anteriores como guía obligatoria.
- **Comprobado:** el árbol de trabajo estaba limpio al comenzar. Repeat V2 mantiene un import y llamadas al motor compartido en `repeat_engine_adapter.py`. No se ejecutó una auditoría completa de dependencias ni se reevaluaron los defectos del documento 40.
- **Cambios documentales:** creado este documento; ajustadas las entradas de `AGENTS.md` y `README.md` para que las sesiones futuras usen esta directriz. Se conservan los documentos anteriores.
- **Resultado:** nueva orientación registrada. No se modificaron Python, JavaScript, HTML, CSS, schema ni jobs. No se creó una habilidad, no se reinició Flask y no se ejecutaron suites del editor en esta intervención documental.
- **Validación documental:** comprobados los enlaces locales y el balance de bloques de código de los tres documentos afectados; `git diff --check` sin errores de whitespace. Sin commit en esta intervención.
- **Abierto:** la independencia de código es un requisito adoptado, todavía no una propiedad demostrada del sistema. El trabajo funcional se elegirá durante el uso y la investigación, sin una secuencia impuesta por esta bitácora.
