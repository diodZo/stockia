"""Presupuesto de alcance del MVP de StockIA (método del Bloque 33).

Calcula el presupuesto neto de horas, corrige las estimaciones por novedad,
rechaza funcionalidades que dependen de sistemas reales, prioriza las tareas
imprescindibles y verifica que el plan cubra las capas obligatorias.

Un total de horas que cabe en el presupuesto NO implica un MVP viable: el plan
solo es viable si entran todas las imprescindibles y se cubren todas las capas.

Uso:
    py presupuesto_alcance.py        (o python presupuesto_alcance.py)

Código de salida: 0 si el MVP es viable; 1 en caso contrario.
Solo usa la librería estándar (Python 3.10+).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

HORAS_DISPONIBLES = 20
FACTOR_NOVEDAD = 1.5
RESERVA_PRUEBAS_DOCS = 0.30
MARGEN_IMPREVISTOS = 0.20

IMPRESCINDIBLE = "imprescindible"
DESEABLE = "deseable"
FUERA_DE_ALCANCE = "fuera de alcance"
ORDEN_PRIORIDAD = {IMPRESCINDIBLE: 0, DESEABLE: 1, FUERA_DE_ALCANCE: 2}

CAPA_API = "api"
CAPA_INVENTARIO_IA = "consulta de inventario / componente IA"
CAPA_CONTENEDOR = "contenedor"
CAPAS_OBLIGATORIAS = (CAPA_API, CAPA_INVENTARIO_IA, CAPA_CONTENEDOR)

# RF clasificados como imprescindibles en docs/ficha_diseno_funcional.md.
RF_IMPRESCINDIBLES = ("RF-01", "RF-02", "RF-03", "RF-04")


@dataclass(frozen=True)
class Tarea:
    nombre: str
    requerimientos: tuple[str, ...]
    horas_base: float
    prioridad: str
    capa: str | None = None
    novedad: bool = False
    requiere_sistema_real: bool = False

    @property
    def horas_ajustadas(self) -> float:
        return round(self.horas_base * (FACTOR_NOVEDAD if self.novedad else 1.0), 2)


@dataclass
class Plan:
    presupuesto_neto: float
    dentro: list[Tarea] = field(default_factory=list)
    fuera: list[tuple[Tarea, str]] = field(default_factory=list)

    @property
    def horas_usadas(self) -> float:
        return round(sum(t.horas_ajustadas for t in self.dentro), 2)

    @property
    def imprescindibles_fuera(self) -> list[Tarea]:
        return [t for t, _ in self.fuera if t.prioridad == IMPRESCINDIBLE]

    @property
    def capas_faltantes(self) -> list[str]:
        cubiertas = {t.capa for t in self.dentro}
        return [c for c in CAPAS_OBLIGATORIAS if c not in cubiertas]

    @property
    def rf_imprescindibles_sin_cubrir(self) -> list[str]:
        cubiertos = {r for t in self.dentro for r in t.requerimientos}
        return [rf for rf in RF_IMPRESCINDIBLES if rf not in cubiertos]

    @property
    def es_viable(self) -> bool:
        return (
            not self.imprescindibles_fuera
            and not self.capas_faltantes
            and not self.rf_imprescindibles_sin_cubrir
        )


# Estimaciones del MVP. "novedad=True" marca tecnología nueva para el equipo,
# cuya estimación base se corrige por FACTOR_NOVEDAD. Las tareas sin novedad
# reutilizan componentes conocidos del Gate 2.
TAREAS_STOCKIA: tuple[Tarea, ...] = (
    Tarea("API REST", ("RF-01",), 2.0, IMPRESCINDIBLE, CAPA_API, novedad=True),
    Tarea("Búsqueda de productos", ("RF-02",), 1.5, IMPRESCINDIBLE, CAPA_INVENTARIO_IA),
    Tarea("Consulta de existencias", ("RF-03",), 2.0, IMPRESCINDIBLE, CAPA_INVENTARIO_IA),
    Tarea("Respuesta con fuente y cantidad", ("RF-04",), 2.0, IMPRESCINDIBLE, CAPA_INVENTARIO_IA),
    Tarea("Docker y configuración", ("RNF-04",), 1.0, IMPRESCINDIBLE, CAPA_CONTENEDOR, novedad=True),
    Tarea("Compatibilidades con documentación (Chroma)", ("RF-05",), 2.0, DESEABLE, CAPA_INVENTARIO_IA, novedad=True),
    Tarea("Conector HTTP/PHP con datos simulados", ("RF-06",), 2.0, DESEABLE, CAPA_INVENTARIO_IA, novedad=True),
    Tarea("Modificar existencias / registrar movimientos", ("RF-07",), 3.0, FUERA_DE_ALCANCE, requiere_sistema_real=True),
    Tarea("Integración con WhatsApp", ("RF-08",), 3.0, FUERA_DE_ALCANCE, novedad=True, requiere_sistema_real=True),
)


def presupuesto_neto(
    horas: float = HORAS_DISPONIBLES,
    reserva: float = RESERVA_PRUEBAS_DOCS,
    margen: float = MARGEN_IMPREVISTOS,
) -> float:
    """Horas para construir tras descontar pruebas/documentación e imprevistos."""
    if horas <= 0:
        raise ValueError("Las horas disponibles deben ser positivas.")
    if reserva < 0 or margen < 0 or reserva + margen >= 1:
        raise ValueError("Reserva y margen deben ser no negativos y sumar menos de 1.")
    return round(horas * (1 - reserva - margen), 2)


def planificar(tareas: tuple[Tarea, ...] | list[Tarea], horas_netas: float) -> Plan:
    """Asigna tareas por prioridad sin superar el presupuesto neto."""
    plan = Plan(presupuesto_neto=horas_netas)
    ordenadas = sorted(tareas, key=lambda t: (ORDEN_PRIORIDAD[t.prioridad], t.requerimientos))
    restante = horas_netas
    for tarea in ordenadas:
        if tarea.requiere_sistema_real:
            plan.fuera.append((tarea, "rechazada: requiere sistemas o credenciales reales"))
        elif tarea.prioridad == FUERA_DE_ALCANCE:
            plan.fuera.append((tarea, "clasificada fuera de alcance"))
        elif tarea.horas_ajustadas <= restante + 1e-9:
            plan.dentro.append(tarea)
            restante -= tarea.horas_ajustadas
        else:
            plan.fuera.append((tarea, f"sin horas: requiere {tarea.horas_ajustadas:g} h, quedan {restante:g} h"))
    return plan


def informe(plan: Plan) -> str:
    lineas = [
        "PRESUPUESTO DE ALCANCE — StockIA (Bloque 33)",
        f"Horas disponibles:           {HORAS_DISPONIBLES:g} h",
        f"Reserva pruebas/docs ({RESERVA_PRUEBAS_DOCS:.0%}):  {HORAS_DISPONIBLES * RESERVA_PRUEBAS_DOCS:g} h",
        f"Margen imprevistos ({MARGEN_IMPREVISTOS:.0%}):   {HORAS_DISPONIBLES * MARGEN_IMPREVISTOS:g} h",
        f"Presupuesto neto:            {plan.presupuesto_neto:g} h",
        f"Factor de novedad:           x{FACTOR_NOVEDAD:g}",
        "",
        "DENTRO DEL ALCANCE:",
    ]
    for t in plan.dentro:
        nov = f" (base {t.horas_base:g} h x{FACTOR_NOVEDAD:g})" if t.novedad else ""
        lineas.append(f"  [{t.prioridad}] {', '.join(t.requerimientos)} {t.nombre}: {t.horas_ajustadas:g} h{nov}")
    lineas.append(f"  Total: {plan.horas_usadas:g} h de {plan.presupuesto_neto:g} h")
    lineas += ["", "FUERA DEL ALCANCE:"]
    for t, motivo in plan.fuera:
        lineas.append(f"  [{t.prioridad}] {', '.join(t.requerimientos)} {t.nombre} ({t.horas_ajustadas:g} h): {motivo}")
    lineas += ["", "CAPAS OBLIGATORIAS:"]
    cubiertas = {t.capa for t in plan.dentro}
    for capa in CAPAS_OBLIGATORIAS:
        lineas.append(f"  {'OK' if capa in cubiertas else 'FALTA'}: {capa}")
    lineas.append("")
    if plan.imprescindibles_fuera:
        nombres = ", ".join(t.nombre for t in plan.imprescindibles_fuera)
        lineas.append(f"ALERTA: imprescindibles fuera por falta de horas o restricciones: {nombres}")
    else:
        lineas.append("Ninguna tarea imprescindible queda fuera.")
    if plan.rf_imprescindibles_sin_cubrir:
        lineas.append(f"ALERTA: RF imprescindibles sin tarea en el plan: {', '.join(plan.rf_imprescindibles_sin_cubrir)}")
    else:
        lineas.append(f"RF imprescindibles cubiertos: {', '.join(RF_IMPRESCINDIBLES)}")
    lineas.append("RESULTADO: MVP viable" if plan.es_viable else "RESULTADO: MVP NO viable")
    return "\n".join(lineas)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    plan =planificar(TAREAS_STOCKIA, presupuesto_neto())
    print(informe(plan))
    return 0 if plan.es_viable else 1


if __name__ == "__main__":
    sys.exit(main())
