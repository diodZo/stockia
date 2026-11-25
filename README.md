# stockia
Inteligencia que conoce tu inventario.  Asistente inteligente de inventarios para microempresas.

## Qué es StockIA

StockIA es un asistente de consulta de inventarios para microempresas. Permite que el personal de venta pregunte por un producto (SKU, nombre o descripción) y reciba su disponibilidad con la fuente de los datos, o una abstención explícita cuando la información no basta. El caso de referencia es GL Repuestos, una tienda de repuestos y accesorios para motocicletas. El MVP trabaja solo con datos ficticios, en modo de solo lectura.

> Estado: **Bloque 33** (diseño, alcance y arquitectura). La aplicación todavía no está implementada.

## Documentación

- [Ficha de diseño funcional](docs/ficha_diseno_funcional.md): problema de negocio, requerimientos y alcance del MVP, arquitectura.
- [Diagrama de arquitectura](docs/diagrama_arquitectura.png) (fuente editable: [docs/generar_diagrama.py](docs/generar_diagrama.py), requiere Pillow).

## Verificaciones del Bloque 33

Requieren Python 3.10+ y solo la librería estándar (en Windows, `py` en lugar de `python` si `python` no está en el PATH):

```powershell
python presupuesto_alcance.py           # presupuesto de 20 h y alcance del MVP
python verificar_ficha.py               # verifica la ficha y el diagrama
python -m unittest discover -s tests    # pruebas de ambos scripts
```
