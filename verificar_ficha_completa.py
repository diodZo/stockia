"""Verificador completo de la ficha de diseño funcional de StockIA (Bloque 34).

Ejecuta las validaciones del Bloque 33 (verificar_ficha.py) y además comprueba
las secciones 4 y 5 y el registro de revisión cruzada (docs/revision_alcance.md).

No se limita al formato: contrasta referencias cruzadas, cobertura, datos de
prueba citados en los criterios, casos negativos, horas frente a las estimaciones
de presupuesto_alcance.py y la coherencia del registro de revisión. Lo que no se
puede decidir automáticamente se lista como "requiere juicio humano" y nunca se
da por aprobado.

Uso:
    py verificar_ficha_completa.py [--ficha RUTA] [--revision RUTA] [--raiz DIR]

Códigos de salida:
    0  ficha y registro de revisión cumplen todas las comprobaciones automáticas
    1  la ficha tiene errores
    2  la ficha cumple, pero el registro de revisión falta, está PENDIENTE o incompleto
Solo usa la librería estándar (Python 3.10+).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import ficha_datos as fd
import presupuesto_alcance as pa
import verificar_ficha as vf

SALIDA_OK = 0
SALIDA_ERRORES_FICHA = 1
SALIDA_REVISION_PENDIENTE = 2

MARCAS_PENDIENTES = (re.compile(r"\[PENDIENTE"), re.compile(re.escape(vf.MARCA_COMPLETAR)))
EXPRESIONES_VAGAS = (
    "funciona correctamente", "correctamente", "es intuitiv", "responde bien",
    "adecuadamente", "de forma adecuada", "rápidamente", "amigable", "user-friendly",
)
RE_DECLARA_CUMPLIDO = re.compile(
    r"\b(?:está|están|queda|quedan|fue|fueron)\s+(?:cumplid|aprobad|verificad|validad)\w*", re.IGNORECASE
)
RE_PREGUNTA = re.compile(r'\{"pregunta": "([^"]*)"\}')
RE_SKU_ESPERADO = re.compile(r'producto\.sku = "(DEMO-\d{3})"')
RE_NOMBRE_ESPERADO = re.compile(r'producto\.nombre = "([^"]+)"')
RE_CANTIDAD = re.compile(r"cantidad = (\d+)")
RE_PROPORCION = re.compile(r"(\d+) de (\d+)")

TIPOS_REVISION = ("revisión cruzada", "autorrevisión")
CAMPOS_REVISION = ("Revisor", "Tipo de revisión", "Fecha de revisión", "Fecha de término de la ficha")
PALABRAS_ULTIMO_HITO = ("pruebas", "documentación", "defensa")

JUICIO_HUMANO = (
    "Que cada criterio sea pertinente para el negocio y suficiente para su requerimiento.",
    "Que las estimaciones de horas de cada hito sean realistas (aquí solo se comprueba que no bajen de las del presupuesto).",
    "Que los datos de prueba ficticios sean representativos del inventario de una tienda de repuestos.",
    "Que la detección de casos negativos (heurística sobre el texto) corresponda a la intención de cada criterio.",
    "Que el revisor sea una persona real, la fecha sea verdadera y los hallazgos sean auténticos.",
    "Que las decisiones sobre los hallazgos estén bien justificadas.",
)


# --- Utilidades -------------------------------------------------------------

def _palabras(texto: str) -> set[str]:
    return {p for p in re.findall(r"\w+", texto.casefold()) if len(p) >= 4 or p.isdigit()}


def _orden(ids: list[str], prefijo: str) -> list[int]:
    return [int(i[len(prefijo):]) for i in ids]


def _correlativo(ids: list[str], prefijo: str, etiqueta: str) -> list[str]:
    errores = []
    duplicados = sorted({i for i in ids if ids.count(i) > 1})
    if duplicados:
        errores.append(f"{etiqueta} duplicados: {', '.join(duplicados)}.")
    numeros = sorted(set(_orden(ids, prefijo)))
    if numeros and numeros != list(range(1, len(numeros) + 1)):
        errores.append(f"La numeración de {etiqueta.lower()} no es correlativa desde 1: {numeros}.")
    return errores


# --- Comprobaciones de la ficha --------------------------------------------

def verificar_marcas(texto: str, ficha: fd.Ficha) -> list[str]:
    errores = []
    for num in (4, 5):
        if ficha.cuerpos.get(num, "").strip() == vf.MARCA_PENDIENTE:
            errores.append(f"La sección {num} sigue pendiente.")
    for patron in MARCAS_PENDIENTES:
        if patron.search(texto):
            errores.append(f"La ficha contiene la marca '{patron.pattern.replace(chr(92), '')}'.")
    return errores


def verificar_criterios(ficha: fd.Ficha) -> list[str]:
    errores = []
    if not ficha.criterios:
        errores.append("No hay criterios de aceptación con el formato '- CA-NN (RF-NN): descripción'.")
    for linea in ficha.criterios_mal_formados:
        errores.append(f"Criterio mal formado: '{linea[:80]}'.")
    errores += _correlativo(ficha.ids_criterios, "CA-", "Criterios")
    for c in ficha.criterios:
        inexistentes = [r for r in c.refs if r not in ficha.ids_requerimientos]
        if inexistentes:
            errores.append(f"{c.id} referencia requerimientos inexistentes: {', '.join(inexistentes)}.")
        bajo = c.texto.casefold()
        vagas = [v for v in EXPRESIONES_VAGAS if v in bajo]
        if vagas:
            errores.append(f"{c.id} usa expresiones vagas: {', '.join(vagas)}.")
        if not re.search(r"\d|`", c.texto):
            errores.append(f"{c.id} no tiene un valor observable (cifra o literal entre comillas invertidas).")
    cuerpo4 = ficha.cuerpos.get(4, "")
    m = RE_DECLARA_CUMPLIDO.search(cuerpo4)
    if m:
        errores.append(f"La sección 4 declara criterios como ya cumplidos ('{m.group(0)}'); deben ser objetivos.")
    return errores


def verificar_cobertura(ficha: fd.Ficha) -> list[str]:
    errores = []
    if not ficha.imprescindibles:
        errores.append("No se pudieron leer los RF imprescindibles de la sección 2.")
    for r in ficha.imprescindibles_sin_criterio:
        errores.append(f"El requerimiento imprescindible {r} no tiene criterio de aceptación.")
    for r in ficha.rnf_sin_criterio:
        errores.append(f"El requerimiento no funcional {r} no tiene criterio de aceptación.")
    return errores


def casos_requeridos_por_rnf02(ficha: fd.Ficha) -> int:
    for rnf_id, resto in ficha.rnf:
        if rnf_id == "RNF-02":
            m = RE_PROPORCION.search(resto)
            if m:
                return int(m.group(2))
    return 0


def verificar_datos_prueba(ficha: fd.Ficha) -> list[str]:
    errores = []
    if not ficha.productos:
        return ["No hay tabla de datos de prueba ficticios ('| DEMO-NNN | nombre | descripción | existencias |')."]
    skus = [p.sku for p in ficha.productos]
    nombres = [p.nombre.casefold() for p in ficha.productos]
    if len(set(skus)) != len(skus):
        errores.append("Hay SKU duplicados en los datos de prueba.")
    if len(set(nombres)) != len(nombres):
        errores.append("Hay nombres de producto duplicados en los datos de prueba.")
    requeridos = casos_requeridos_por_rnf02(ficha)
    if requeridos and len(ficha.productos) < requeridos:
        errores.append(f"RNF-02 exige {requeridos} casos de referencia y los datos de prueba tienen {len(ficha.productos)}.")

    for c in ficha.criterios:
        esperados = RE_SKU_ESPERADO.findall(c.texto)
        for sku in esperados:
            if ficha.producto(sku) is None:
                errores.append(f"{c.id} espera el SKU {sku}, que no está en los datos de prueba.")
        unicos = sorted(set(esperados))
        if len(unicos) == 1 and (p := ficha.producto(unicos[0])):
            for valor in RE_CANTIDAD.findall(c.texto):
                if int(valor) != p.existencias:
                    errores.append(f"{c.id} espera cantidad = {valor} para {p.sku}, pero los datos de prueba indican {p.existencias}.")
            for nombre in RE_NOMBRE_ESPERADO.findall(c.texto):
                if nombre != p.nombre:
                    errores.append(f"{c.id} espera el nombre '{nombre}' para {p.sku}, pero los datos de prueba indican '{p.nombre}'.")
        abstencion = 'estado = "abstencion"' in c.texto
        for pregunta in RE_PREGUNTA.findall(c.texto):
            for sku in fd.RE_SKU.findall(pregunta):
                if abstencion and ficha.producto(sku):
                    errores.append(f"{c.id} espera abstención para {sku}, que sí existe en los datos de prueba.")
                if not abstencion and esperados and sku not in esperados:
                    errores.append(f"{c.id} pregunta por {sku} pero espera {', '.join(unicos)}.")
    return errores


def detectar_casos(ficha: fd.Ficha) -> dict[str, list[str]]:
    """Devuelve, para cada caso exigido por el Bloque 34, los criterios que lo cubren."""
    casos: dict[str, list[str]] = {
        "SKU existente": [],
        "SKU inexistente": [],
        "Pregunta vacía o inválida": [],
        "Búsqueda por descripción": [],
        "Producto sin existencias": [],
        "Consulta sin información suficiente": [],
        "Verificación de que no inventa cantidades": [],
    }
    for c in ficha.criterios:
        preguntas = RE_PREGUNTA.findall(c.texto)
        esperados = set(RE_SKU_ESPERADO.findall(c.texto))
        abstencion = 'estado = "abstencion"' in c.texto
        for pregunta in preguntas:
            skus = fd.RE_SKU.findall(pregunta)
            if any(s in esperados and ficha.producto(s) for s in skus):
                casos["SKU existente"].append(c.id)
            if abstencion and any(ficha.producto(s) is None for s in skus):
                casos["SKU inexistente"].append(c.id)
            if abstencion and not skus:
                casos["Consulta sin información suficiente"].append(c.id)
            for sku in esperados:
                p = ficha.producto(sku)
                if p is None:
                    continue
                bajo = pregunta.casefold()
                if sku not in pregunta and p.nombre.casefold() not in bajo \
                        and len(_palabras(pregunta) & _palabras(p.descripcion)) >= 3:
                    casos["Búsqueda por descripción"].append(c.id)
        if "error_validacion" in c.texto and "422" in c.texto:
            casos["Pregunta vacía o inválida"].append(c.id)
        for sku in esperados:
            p = ficha.producto(sku)
            if p and p.existencias == 0 and "cantidad = 0" in c.texto:
                casos["Producto sin existencias"].append(c.id)
        if "cantidad = null" in c.texto and "RNF-02" in c.refs:
            casos["Verificación de que no inventa cantidades"].append(c.id)
    return {k: sorted(set(v)) for k, v in casos.items()}


def verificar_casos_negativos(ficha: fd.Ficha) -> list[str]:
    return [f"No hay un criterio verificable para el caso: {caso}." for caso, cas in detectar_casos(ficha).items() if not cas]


def verificar_hitos(ficha: fd.Ficha) -> list[str]:
    errores = []
    if not ficha.hitos:
        return ["No hay hitos con el formato '- H1 (3 h): Descripción. Cubre: RF-01. Se comprueba con: CA-01.'."]
    for linea in ficha.hitos_mal_formados:
        errores.append(f"Hito mal formado: '{linea[:80]}'.")
    errores += _correlativo([h.id for h in ficha.hitos], "H", "Hitos")
    ids_ca = set(ficha.ids_criterios)
    for h in ficha.hitos:
        if not h.criterios:
            errores.append(f"El hito {h.id} no tiene criterios de aceptación.")
        if not h.cubre:
            errores.append(f"El hito {h.id} no declara requerimientos cubiertos.")
        for ca in h.criterios:
            if ca not in ids_ca:
                errores.append(f"El hito {h.id} referencia el criterio inexistente {ca}.")
        for req in h.cubre:
            if req not in ficha.ids_requerimientos:
                errores.append(f"El hito {h.id} referencia el requerimiento inexistente {req}.")
            elif not any(req in c.refs for c in ficha.criterios if c.id in h.criterios):
                errores.append(f"El hito {h.id} declara cubrir {req}, pero ninguno de sus criterios lo comprueba.")
    for ca in ficha.criterios_sin_hito:
        errores.append(f"El criterio {ca} no está asignado a ningún hito.")

    construccion = ficha.hitos[:-1]
    for c in ficha.criterios:
        if c.id not in ficha.criterios_sin_hito and not any(c.id in h.criterios for h in construccion):
            errores.append(f"El criterio {c.id} solo se comprueba en el hito final; falta un hito de construcción.")
    cubiertos = {r for h in construccion for r in h.cubre}
    for req in ficha.imprescindibles + [i for i, _ in ficha.rnf]:
        if req not in cubiertos:
            errores.append(f"{req} no está cubierto por ningún hito de construcción.")
    return errores


def verificar_presupuesto(ficha: fd.Ficha) -> list[str]:
    errores = []
    if not ficha.hitos:
        return errores
    margen = round(pa.HORAS_DISPONIBLES * pa.MARGEN_IMPREVISTOS, 2)
    reserva = round(pa.HORAS_DISPONIBLES * pa.RESERVA_PRUEBAS_DOCS, 2)
    maximo = round(pa.HORAS_DISPONIBLES - margen, 2)
    total = ficha.horas_planificadas
    if total > maximo + 1e-9:
        errores.append(f"Presupuesto excedido: los hitos suman {total:g} h y el máximo es {maximo:g} h "
                       f"({pa.HORAS_DISPONIBLES:g} h menos {margen:g} h de margen sin asignar).")

    ultimo = ficha.hitos[-1]
    texto_ultimo = ultimo.descripcion.casefold()
    faltan = [p for p in PALABRAS_ULTIMO_HITO if p not in texto_ultimo]
    if faltan:
        errores.append(f"El último hito ({ultimo.id}) debe corresponder a pruebas, documentación y defensa; falta: {', '.join(faltan)}.")
    if abs(ultimo.horas - reserva) > 1e-9:
        errores.append(f"El último hito ({ultimo.id}) tiene {ultimo.horas:g} h; la reserva de pruebas y documentación es {reserva:g} h.")

    construccion = ficha.hitos[:-1]
    neto = pa.presupuesto_neto()
    horas_construccion = round(sum(h.horas for h in construccion), 2)
    if horas_construccion > neto + 1e-9:
        errores.append(f"Los hitos de construcción suman {horas_construccion:g} h y el presupuesto neto es {neto:g} h.")

    # Cada tarea del plan de presupuesto_alcance.py se asigna al primer hito de
    # construcción que cubre alguno de sus requerimientos. Un hito no puede tener
    # menos horas que las estimaciones de sus tareas (no se reducen para cuadrar).
    asignadas: dict[str, float] = {h.id: 0.0 for h in construccion}
    for tarea in pa.planificar(pa.TAREAS_STOCKIA, neto).dentro:
        hito = next((h for h in construccion if set(tarea.requerimientos) & set(h.cubre)), None)
        if hito is None:
            errores.append(f"La tarea '{tarea.nombre}' ({', '.join(tarea.requerimientos)}, "
                           f"{tarea.horas_ajustadas:g} h) no está en ningún hito de construcción.")
        else:
            asignadas[hito.id] += tarea.horas_ajustadas
    for h in construccion:
        if h.horas + 1e-9 < asignadas[h.id]:
            errores.append(f"El hito {h.id} tiene {h.horas:g} h, menos que las {asignadas[h.id]:g} h estimadas "
                           f"para sus tareas en presupuesto_alcance.py.")
    return errores


# --- Registro de revisión ---------------------------------------------------

def _fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        return None


def verificar_revision(revision: fd.Revision | None, hoy: date | None = None) -> list[str]:
    hoy = hoy or date.today()
    if revision is None:
        return ["Registro de revisión ausente: no existe docs/revision_alcance.md."]
    errores = []
    if "PENDIENTE" in revision.texto:
        errores.append("El registro de revisión está marcado como PENDIENTE.")
    for campo in CAMPOS_REVISION:
        if not revision.campos.get(campo):
            errores.append(f"Falta el campo '{campo}' en el registro de revisión.")

    tipo = revision.campos.get("Tipo de revisión", "").casefold()
    if tipo and tipo not in TIPOS_REVISION:
        errores.append(f"Tipo de revisión no válido: '{tipo}' (se espera: {' o '.join(TIPOS_REVISION)}).")
    f_rev = _fecha(revision.campos.get("Fecha de revisión", ""))
    f_fin = _fecha(revision.campos.get("Fecha de término de la ficha", ""))
    if revision.campos.get("Fecha de revisión") and f_rev is None:
        errores.append("La fecha de revisión no tiene formato AAAA-MM-DD.")
    if revision.campos.get("Fecha de término de la ficha") and f_fin is None:
        errores.append("La fecha de término de la ficha no tiene formato AAAA-MM-DD.")
    if f_rev and f_rev > hoy:
        errores.append(f"La fecha de revisión ({f_rev}) es futura.")
    if f_rev and f_fin and f_rev < f_fin:
        errores.append("La revisión es anterior a la fecha de término de la ficha.")
    if tipo == "autorrevisión" and f_rev and f_fin and f_rev < f_fin + timedelta(days=1):
        errores.append("Una autorrevisión exige al menos un día desde la terminación de la ficha.")

    if len(revision.hallazgos) < 2:
        errores.append(f"El registro tiene {len(revision.hallazgos)} hallazgos; se requieren al menos 2.")
    numeros = [h.numero for h in revision.hallazgos]
    if numeros and numeros != list(range(1, len(numeros) + 1)):
        errores.append(f"Los hallazgos no están numerados de forma correlativa desde 1: {numeros}.")
    for h in revision.hallazgos:
        if not h.descripcion:
            errores.append(f"El hallazgo {h.numero} no tiene descripción.")
        if h.decision is None:
            errores.append(f"El hallazgo {h.numero} no tiene en la línea siguiente '  Decisión: aceptado|rechazado|aplazado. "
                           f"Cambio|Justificación: ...' con exactamente dos espacios.")
        elif h.decision == "aceptado" and h.tipo_detalle != "Cambio":
            errores.append(f"El hallazgo {h.numero} está aceptado y debe describir el 'Cambio' aplicado.")
        elif h.decision in ("rechazado", "aplazado") and h.tipo_detalle != "Justificación":
            errores.append(f"El hallazgo {h.numero} está {h.decision} y debe incluir 'Justificación'.")
    if not any(revision.aciertos):
        errores.append("El registro no identifica ningún acierto ('- Acierto: ...').")
    return errores


# --- Orquestación -------------------------------------------------------------

def comprobaciones_ficha(texto: str, raiz: Path) -> list[tuple[str, list[str]]]:
    ficha = fd.cargar_ficha(texto)
    return [
        ("Validaciones del Bloque 33 (secciones 1 a 3 y diagrama)", vf.verificar(texto, raiz)),
        ("Secciones sin marcas pendientes", verificar_marcas(texto, ficha)),
        ("Criterios de aceptación: formato, unicidad y referencias", verificar_criterios(ficha)),
        ("Cobertura de imprescindibles y RNF", verificar_cobertura(ficha)),
        ("Datos de prueba citados en los criterios", verificar_datos_prueba(ficha)),
        ("Casos negativos y de borde exigidos", verificar_casos_negativos(ficha)),
        ("Hitos: formato, criterios y cobertura", verificar_hitos(ficha)),
        ("Presupuesto de horas", verificar_presupuesto(ficha)),
    ]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ficha", type=Path, default=fd.FICHA_POR_DEFECTO)
    parser.add_argument("--revision", type=Path, default=fd.REVISION_POR_DEFECTO)
    parser.add_argument("--raiz", type=Path, default=fd.RAIZ)
    args = parser.parse_args(argv)

    if not args.ficha.is_file():
        print(f"ERROR: no existe la ficha {args.ficha}")
        return SALIDA_ERRORES_FICHA

    print("VERIFICACIÓN COMPLETA DE LA FICHA — StockIA (Bloque 34)")
    print("\nComprobaciones automáticas de la ficha:")
    errores_ficha = 0
    for nombre, errores in comprobaciones_ficha(args.ficha.read_text(encoding="utf-8"), args.raiz):
        print(f"  [{'OK' if not errores else 'FALLO'}] {nombre}")
        for e in errores:
            print(f"      - {e}")
        errores_ficha += len(errores)

    errores_rev = verificar_revision(fd.leer_revision(args.revision))
    print("\nComprobaciones automáticas del registro de revisión:")
    print(f"  [{'OK' if not errores_rev else 'PENDIENTE'}] {args.revision.name}")
    for e in errores_rev:
        print(f"      - {e}")

    print("\nRequieren juicio humano (no se aprueban automáticamente):")
    for item in JUICIO_HUMANO:
        print(f"  - {item}")

    print()
    if errores_ficha:
        print(f"RESULTADO: la ficha NO cumple ({errores_ficha} errores).")
        return SALIDA_ERRORES_FICHA
    if errores_rev:
        print("RESULTADO: ficha técnicamente completa; revisión cruzada PENDIENTE o incompleta. Bloque no entregable.")
        return SALIDA_REVISION_PENDIENTE
    print("RESULTADO: todas las comprobaciones automáticas pasan. Falta la validación humana listada arriba.")
    return SALIDA_OK


if __name__ == "__main__":
    sys.exit(main())
