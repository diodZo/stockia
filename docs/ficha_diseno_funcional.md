# Ficha de diseño funcional — StockIA

> Proyecto: StockIA, consulta de inventarios para microempresas.
> Caso de referencia: GL Repuestos (repuestos y accesorios para motocicletas).
> Estado: secciones 1 a 3 completas en el Bloque 33; secciones 4 y 5 pendientes para el Bloque 34.

## 1. Problema de negocio

**Quién tiene el problema.** En GL Repuestos, empresa que comercializa repuestos y accesorios para motocicletas, las vendedoras atienden a clientes que preguntan por productos concretos. Cuando no conocen un producto, su disponibilidad o su compatibilidad con un modelo de motocicleta, deben interrumpir al responsable del inventario para obtener la respuesta.

**Qué sucede.** Cada duda se resuelve de forma manual y depende de una sola persona. Mientras el responsable del inventario responde, deja de hacer su propio trabajo, y el cliente espera en el mostrador o en la conversación. Si el responsable no está disponible, la venta se retrasa o la información entregada puede ser imprecisa.

**Cuánto tiempo requiere.** Estimación preliminar, a partir de lo informado por el negocio:

| Variable | Mínimo | Intermedio | Máximo |
|---|---|---|---|
| Consultas diarias | 10 | 15 | 20 |
| Minutos por consulta | 5 | 7,5 | 10 |
| Días mensuales (supuesto de cálculo) | 22 | 22 | 22 |
| Consultas mensuales | 220 | 330 | 440 |
| Tiempo mensual dedicado | 18 h 20 min | 41 h 15 min | 73 h 20 min |

Los 22 días mensuales son solo un supuesto de cálculo. Estas cifras son estimaciones preliminares, no mediciones instrumentadas; deberán contrastarse con un registro real de consultas.

**Qué mejora se espera.** El objetivo preliminar es reducir al menos un 50 % del tiempo dedicado a responder estas consultas, sujeto a validación posterior. En el escenario intermedio, esto equivale a liberar al menos 20 h 37 min mensuales del responsable del inventario y a que las vendedoras obtengan respuestas sobre producto, disponibilidad y compatibilidad sin depender de su presencia.

## 2. Requerimientos y alcance (MVP)

### Requerimientos funcionales

| ID | Requerimiento |
|---|---|
| RF-01 | Recibir una pregunta de inventario mediante API REST y devolver la respuesta en JSON. |
| RF-02 | Buscar productos por SKU, nombre o descripción. |
| RF-03 | Consultar cantidades disponibles mediante un conector autorizado de solo lectura. |
| RF-04 | Entregar una respuesta que identifique el producto, la cantidad y la fuente, o una abstención explícita cuando falten datos. |
| RF-05 | Consultar compatibilidades respaldadas por documentación. |
| RF-06 | Integrar un inventario externo mediante conector HTTP/PHP. |
| RF-07 | Modificar existencias o registrar movimientos. |
| RF-08 | Integrar WhatsApp. |

### Requerimientos no funcionales

| ID | Requerimiento | Criterio medible |
|---|---|---|
| RNF-01 | Tiempo de respuesta | Al menos 9 de 10 consultas DEMO se responden en 5 segundos o menos. |
| RNF-02 | Exactitud de cantidades | Las cantidades coinciden con la fuente simulada en 20 de 20 casos de referencia. |
| RNF-03 | Privacidad de logs | 0 de 20 consultas de prueba dejan credenciales, preguntas completas o información sensible en logs. |
| RNF-04 | Facilidad de despliegue | El servicio se inicia siguiendo el README y Docker en un máximo de 10 minutos en el entorno de prueba definido. |
| RNF-05 | Trazabilidad | 20 de 20 consultas de prueba (100 %) devuelven trace ID y estado. |

### Clasificación del alcance

Imprescindible: RF-01, RF-02, RF-03, RF-04
Deseable: RF-05, RF-06
Fuera de alcance: RF-07, RF-08

**Motivos.**

- **Imprescindibles (RF-01 a RF-04).** Forman el flujo mínimo que resuelve el problema de la sección 1: la vendedora pregunta (RF-01), el servicio encuentra el producto (RF-02), obtiene la cantidad desde un origen autorizado (RF-03) y responde citando la fuente o se abstiene (RF-04). Si falta cualquiera de los cuatro, el MVP no responde una consulta de disponibilidad de forma verificable. Son 4 imprescindibles, dentro del máximo de 5.
- **Deseables (RF-05, RF-06).** Aportan valor, pero no son necesarios para responder disponibilidad. Las compatibilidades (RF-05) requieren documentación técnica curada y pueden incorporarse con Chroma si sobra tiempo. El conector HTTP/PHP (RF-06) demuestra la arquitectura de adaptadores, pero el MVP ya funciona con el conector SQLite.
- **Fuera de alcance (RF-07, RF-08).** Modificar existencias (RF-07) contradice la regla de solo lectura y exige controles de autorización y auditoría que no caben en el presupuesto. WhatsApp (RF-08) requiere cuentas, credenciales y un canal productivo de terceros; además, el presupuesto de alcance rechaza toda funcionalidad que dependa de sistemas reales.

**Separación entre integración simulada y acceso real.** Si se aborda RF-06 dentro del curso, se hará exclusivamente contra un servicio HTTP de prueba con datos ficticios que imite la forma de la respuesta PHP. Cualquier acceso real al inventario de GL Repuestos queda fuera del MVP y del Gate: no se requieren credenciales, datos de producción ni sistemas productivos para evaluar el proyecto.

## 3. Arquitectura de la solución

Diagrama: docs/diagrama_arquitectura.png

![Diagrama de arquitectura de StockIA](diagrama_arquitectura.png)

### Decisiones de arquitectura

| # | Decisión | Elección | Justificación |
|---|---|---|---|
| 1 | Modelo | Gemini mediante API | Modelo definido por el curso; se consume como servicio externo, sin infraestructura propia de inferencia. Interpreta la pregunta y redacta la respuesta, pero nunca es la fuente de las cantidades. La clave se lee de una variable de entorno y nunca se guarda en Git. |
| 2 | Vector store | Chroma (opcional) | Solo para documentación técnica (fichas y compatibilidades, RF-05). Funciona embebido dentro del mismo contenedor, sin servidor adicional. Las existencias no se guardan en Chroma, porque cambian y deben leerse siempre del origen autorizado. |
| 3 | Orquestación | Herramientas de consulta autorizadas y componentes reutilizables del Gate 2 | La Orquestación decide qué herramienta invocar (buscar producto, consultar existencias, buscar documentación) a partir de una lista cerrada. Reutilizar componentes del Gate 2 reduce horas y riesgo. Asigna el trace ID y aplica la abstención. |
| 4 | Exposición | FastAPI con endpoint REST | Cumple RF-01 con un endpoint `POST /consulta` que devuelve JSON validado. Facilita pruebas automatizadas y documentación OpenAPI sin trabajo adicional. |
| 5 | Empaquetado | Docker | Un único contenedor reproducible que cumple RNF-04 (inicio en 10 minutos o menos siguiendo el README) y aísla dependencias del entorno de la persona evaluadora. |

### Fuentes de datos y capa de conectores

- **Conector inicial: SQLite con datos ficticios.** El inventario del MVP es una base SQLite generada con productos, SKU y cantidades inventadas. No se usan datos reales de producción de GL Repuestos.
- **Arquitectura de adaptadores.** La Orquestación no conoce el origen concreto: llama a una interfaz común de la capa de conectores (por ejemplo `buscar_producto(texto)` y `consultar_existencias(sku)`). Cada fuente implementa esa interfaz como un adaptador, de modo que agregar una nueva fuente no cambia la Orquestación ni FastAPI.
- **Posible adaptador HTTP para PHP de GL Repuestos (fuera del MVP).** Se representa en el diagrama como extensión futura, con línea discontinua. En el curso solo podría probarse contra un servicio simulado (RF-06, deseable).

### Reglas de seguridad y de datos

- **Ninguna ejecución de SQL arbitrario generado por la IA.** El modelo solo elige una herramienta y sus parámetros; los conectores ejecutan consultas predefinidas y parametrizadas.
- **Ninguna modificación de inventario.** Todos los conectores son de solo lectura; no existe herramienta de escritura (RF-07 fuera de alcance).
- **Las existencias provienen siempre del origen autorizado.** La cantidad que se entrega es la que devuelve el conector, con su fuente; el modelo no la estima ni la recuerda.
- **El modelo puede abstenerse.** Si no hay información suficiente (producto no encontrado, ambigüedad o fuente sin datos), la respuesta indica la abstención con su estado y trace ID, en lugar de inventar.
- **Logs sin datos sensibles.** Se registran trace ID, estado y tiempos; no credenciales ni preguntas completas (RNF-03).

## 4. Criterios de aceptación

[PENDIENTE: se completa en el Bloque 34]

## 5. Plan de construcción por hitos

[PENDIENTE: se completa en el Bloque 34]
