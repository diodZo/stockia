# stockia
Inteligencia que conoce tu inventario.  Asistente inteligente de inventarios para microempresas.

## Qué es StockIA

StockIA es un asistente de consulta de inventarios para microempresas. Permite que el personal de venta pregunte por un producto (SKU, nombre o descripción) y reciba su disponibilidad con la fuente de los datos, o una abstención explícita cuando la información no basta. El caso de referencia es GL Repuestos, una tienda de repuestos y accesorios para motocicletas. El MVP trabaja solo con datos ficticios, en modo de solo lectura.

> Estado: **Bloque 34** (criterios de aceptación y plan por hitos), pendiente de revisión cruzada. La aplicación todavía no está implementada.

## Documentación

- [Ficha de diseño funcional](docs/ficha_diseno_funcional.md): problema de negocio, requerimientos y alcance del MVP, arquitectura, criterios de aceptación y plan por hitos.
- [Registro de revisión cruzada](docs/revision_alcance.md): plantilla pendiente de completar por la persona revisora.
- [Diagrama de arquitectura](docs/diagrama_arquitectura.png) (fuente editable: [docs/generar_diagrama.py](docs/generar_diagrama.py), requiere Pillow).

## Verificaciones del Bloque 33

Requieren Python 3.10+ y solo la librería estándar (en Windows, `py` en lugar de `python` si `python` no está en el PATH):

```powershell
python presupuesto_alcance.py           # presupuesto de 20 h y alcance del MVP
python verificar_ficha.py               # verifica la ficha y el diagrama
python -m unittest discover -s tests    # pruebas de ambos scripts
```

## Verificaciones del Bloque 34

```powershell
py resumen_ficha.py                     # conteos, cobertura RF/RNF -> CA -> hito y horas
py verificar_ficha_completa.py          # verificación completa de la ficha y del registro de revisión
py -m unittest discover -s tests        # pruebas de los Bloques 33 y 34
```

`verificar_ficha_completa.py` devuelve 0 si la ficha y el registro de revisión cumplen todas las comprobaciones automáticas; 1 si la ficha tiene errores; 2 si la ficha cumple, pero la revisión cruzada falta, está PENDIENTE o está incompleta. También lista las comprobaciones que requieren juicio humano, que nunca se aprueban automáticamente.
