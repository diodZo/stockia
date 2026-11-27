"""Resumen de la ficha de diseño funcional de StockIA (Bloque 34).

Informa conteos de requerimientos, criterios de aceptación, hitos y horas,
y las brechas de cobertura. Es informativo: no aprueba la ficha
(para eso está verificar_ficha_completa.py).

Uso:
    py resumen_ficha.py [--ficha RUTA]

Código de salida: 0 si la ficha se pudo leer; 1 si no existe.
Solo usa la librería estándar (Python 3.10+).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import ficha_datos as fd
import presupuesto_alcance as pa


def horas_maximas_hitos() -> float:
    """Horas planificables: disponibles menos el margen de imprevistos, que no se asigna."""
    return round(pa.HORAS_DISPONIBLES * (1 - pa.MARGEN_IMPREVISTOS), 2)


def _lista(valores: list[str]) -> str:
    return ", ".join(valores) if valores else "ninguno"


def resumen(ficha: fd.Ficha) -> str:
    c = ficha.clasificacion
    maximo = horas_maximas_hitos()
    lineas = [
        "RESUMEN DE LA FICHA — StockIA (Bloque 34)",
        f"Requerimientos funcionales (RF):     {len(ficha.rf)}",
        f"Requerimientos no funcionales (RNF): {len(ficha.rnf)}",
        f"Imprescindibles:                     {len(c.get('Imprescindible', []))}",
        f"Deseables:                           {len(c.get('Deseable', []))}",
        f"Fuera de alcance:                    {len(c.get('Fuera de alcance', []))}",
        f"Criterios de aceptación:             {len(ficha.criterios)}",
        f"Criterios mal formados:              {len(ficha.criterios_mal_formados)}",
        f"Imprescindibles sin criterio:        {_lista(ficha.imprescindibles_sin_criterio)}",
        f"RNF sin criterio:                    {_lista(ficha.rnf_sin_criterio)}",
        f"Hitos:                               {len(ficha.hitos)}",
        f"Horas planificadas:                  {ficha.horas_planificadas:g} h de {maximo:g} h máximo "
        f"(margen sin asignar: {pa.HORAS_DISPONIBLES - ficha.horas_planificadas:g} h)",
        f"Criterios sin hito:                  {_lista(ficha.criterios_sin_hito)}",
        f"Hitos sin criterio:                  {_lista(ficha.hitos_sin_criterio)}",
        f"Productos ficticios de prueba:       {len(ficha.productos)}",
    ]
    if ficha.criterios:
        lineas += ["", "MATRIZ DE COBERTURA (requerimiento -> criterios -> hitos):"]
        for req in list(ficha.rf) + [i for i, _ in ficha.rnf]:
            cas = ficha.criterios_de(req)
            if not cas:
                continue
            hitos = sorted({h for ca in cas for h in ficha.hitos_de(ca)}, key=lambda x: int(x[1:]))
            lineas.append(f"  {req}: {', '.join(cas)} -> {_lista(hitos)}")
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ficha", type=Path, default=fd.FICHA_POR_DEFECTO)
    args = parser.parse_args(argv)
    if not args.ficha.is_file():
        print(f"ERROR: no existe la ficha {args.ficha}")
        return 1
    print(resumen(fd.leer_ficha(args.ficha)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
