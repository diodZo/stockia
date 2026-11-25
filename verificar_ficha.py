"""Verificador de la ficha de diseño funcional de StockIA (Bloque 33).

Comprueba docs/ficha_diseno_funcional.md y docs/diagrama_arquitectura.png.

Uso:
    py verificar_ficha.py [--ficha RUTA] [--raiz DIRECTORIO]

Código de salida: 0 si la ficha cumple; 1 si hay errores.
Solo usa la librería estándar (Python 3.10+).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
FICHA_POR_DEFECTO = RAIZ / "docs" / "ficha_diseno_funcional.md"
RUTA_DIAGRAMA = "docs/diagrama_arquitectura.png"
REFERENCIA_DIAGRAMA = f"Diagrama: {RUTA_DIAGRAMA}"
MARCA_PENDIENTE = "[PENDIENTE: se completa en el Bloque 34]"
MARCA_COMPLETAR = "[COMPLETAR]"
MENSAJE_OK = "Ficha verificada: secciones 1 a 3 completas"
MAX_IMPRESCINDIBLES = 5
FIRMA_PNG = b"\x89PNG\r\n\x1a\n"

SECCIONES = {
    1: "Problema de negocio",
    2: "Requerimientos y alcance (MVP)",
    3: "Arquitectura de la solución",
    4: "Criterios de aceptación",
    5: "Plan de construcción por hitos",
}

GRUPOS = ("Imprescindible", "Deseable", "Fuera de alcance")

# Términos de tecnología o solución prohibidos en la sección 1.
# "IA" se busca en mayúsculas para no confundirlo con palabras en español.
TERMINOS_PROHIBIDOS_S1 = [
    (r"\bIA\b", 0),
    (r"inteligencia artificial", re.IGNORECASE),
    (r"\bRAG\b", re.IGNORECASE),
    (r"chat\s?bot", re.IGNORECASE),
    (r"\bbot\b", re.IGNORECASE),
    (r"\bGemini\b", re.IGNORECASE),
    (r"\bAPI\b", re.IGNORECASE),
    (r"\bREST\b", 0),
    (r"FastAPI", re.IGNORECASE),
    (r"\bChroma\b", re.IGNORECASE),
    (r"\bDocker\b", re.IGNORECASE),
    (r"\bSQLite\b", re.IGNORECASE),
    (r"\bLLM\b", re.IGNORECASE),
    (r"modelo de lenguaje", re.IGNORECASE),
    (r"\basistente\b", re.IGNORECASE),
    (r"WhatsApp", re.IGNORECASE),
    (r"\bPHP\b", re.IGNORECASE),
    (r"\bPython\b", re.IGNORECASE),
    (r"\bembedding", re.IGNORECASE),
    (r"vector", re.IGNORECASE),
]

RE_ENCABEZADO = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
RE_ENCABEZADO_NUM = re.compile(r"^(\d+)\.\s+(.+)$")
RE_FILA_RF = re.compile(r"^\|\s*(RF-\S*)\s*\|", re.MULTILINE)
RE_FILA_RNF = re.compile(r"^\|\s*(RNF-\S*)\s*\|(.*)$", re.MULTILINE)
RE_ID_RF = re.compile(r"^RF-\d{2}$")
RE_ID_RNF = re.compile(r"^RNF-\d{2}$")
RE_REF_RF = re.compile(r"\bRF-\d{2}\b")


def separar_secciones(texto: str) -> tuple[dict[int, str], list[str]]:
    """Devuelve {número: cuerpo} y la lista de errores de encabezados."""
    errores: list[str] = []
    encontrados: list[tuple[int, str, int, int]] = []
    for m in RE_ENCABEZADO.finditer(texto):
        mn = RE_ENCABEZADO_NUM.match(m.group(1))
        if mn:
            encontrados.append((int(mn.group(1)), mn.group(2), m.start(), m.end()))

    numeros = [n for n, *_ in encontrados]
    for num, titulo in SECCIONES.items():
        coincidencias = [e for e in encontrados if e[0] == num]
        if not coincidencias:
            errores.append(f"Falta la sección '## {num}. {titulo}'.")
        elif len(coincidencias) > 1:
            errores.append(f"La sección {num} aparece {len(coincidencias)} veces.")
        elif coincidencias[0][1] != titulo:
            errores.append(f"La sección {num} debe titularse '{titulo}' (encontrado: '{coincidencias[0][1]}').")
    extra = sorted(set(numeros) - set(SECCIONES))
    if extra:
        errores.append(f"Secciones numeradas no esperadas: {extra}.")
    if numeros != sorted(numeros):
        errores.append("Las secciones no están en orden numérico.")

    cuerpos: dict[int, str] = {}
    for i, (num, _, _, fin) in enumerate(encontrados):
        siguiente = encontrados[i + 1][2] if i + 1 < len(encontrados) else len(texto)
        cuerpos.setdefault(num, texto[fin:siguiente].strip())
    return cuerpos, errores


def verificar_secciones_completas(cuerpos: dict[int, str]) -> list[str]:
    errores = []
    for num in (1, 2, 3):
        cuerpo = cuerpos.get(num)
        if cuerpo is None:
            continue
        if not cuerpo:
            errores.append(f"La sección {num} está vacía.")
        if MARCA_COMPLETAR in cuerpo:
            errores.append(f"La sección {num} contiene {MARCA_COMPLETAR}.")
        if MARCA_PENDIENTE in cuerpo:
            errores.append(f"La sección {num} está marcada como pendiente y debe estar completa.")
    return errores


def verificar_pendientes(cuerpos: dict[int, str]) -> list[str]:
    errores = []
    for num in (4, 5):
        cuerpo = cuerpos.get(num)
        if cuerpo is not None and cuerpo != MARCA_PENDIENTE:
            errores.append(f"La sección {num} debe contener solo '{MARCA_PENDIENTE}' hasta el Bloque 34.")
    return errores


def verificar_problema_sin_tecnologia(cuerpos: dict[int, str]) -> list[str]:
    cuerpo = cuerpos.get(1, "")
    hallados = []
    for patron, flags in TERMINOS_PROHIBIDOS_S1:
        m = re.search(patron, cuerpo, flags)
        if m:
            hallados.append(m.group(0))
    if hallados:
        return [f"La sección 1 menciona tecnología o solución: {', '.join(sorted(set(hallados)))}."]
    return []


def verificar_requerimientos(cuerpos: dict[int, str]) -> list[str]:
    errores: list[str] = []
    cuerpo = cuerpos.get(2, "")

    ids_rf = RE_FILA_RF.findall(cuerpo)
    filas_rnf = RE_FILA_RNF.findall(cuerpo)
    ids_rnf = [i for i, _ in filas_rnf]

    if not ids_rf:
        errores.append("No hay requerimientos funcionales con formato '| RF-NN |'.")
    if not ids_rnf:
        errores.append("No hay requerimientos no funcionales con formato '| RNF-NN |'.")

    for prefijo, ids, patron in (("RF", ids_rf, RE_ID_RF), ("RNF", ids_rnf, RE_ID_RNF)):
        mal = [i for i in ids if not patron.match(i)]
        if mal:
            errores.append(f"Identificadores {prefijo} con formato inválido (se espera {prefijo}-NN): {', '.join(mal)}.")
        duplicados = sorted({i for i in ids if ids.count(i) > 1})
        if duplicados:
            errores.append(f"Identificadores {prefijo} duplicados: {', '.join(duplicados)}.")
        validos = sorted({int(i.split('-')[1]) for i in ids if patron.match(i)})
        if validos and validos != list(range(1, len(validos) + 1)):
            errores.append(f"La numeración {prefijo} no es correlativa desde 01: {validos}.")

    for rnf_id, resto in filas_rnf:
        if not re.search(r"\d", resto):
            errores.append(f"{rnf_id} no tiene un valor numérico medible.")

    errores += verificar_clasificacion(cuerpo, set(ids_rf))
    return errores


def verificar_clasificacion(cuerpo: str, ids_rf: set[str]) -> list[str]:
    errores: list[str] = []
    grupos: dict[str, list[str]] = {}
    for grupo in GRUPOS:
        lineas = re.findall(rf"^{re.escape(grupo)}:(.*)$", cuerpo, re.MULTILINE)
        if not lineas:
            errores.append(f"Falta la línea de clasificación '{grupo}:'.")
            grupos[grupo] = []
        elif len(lineas) > 1:
            errores.append(f"La línea '{grupo}:' aparece más de una vez.")
            grupos[grupo] = [r for linea in lineas for r in RE_REF_RF.findall(linea)]
        else:
            grupos[grupo] = RE_REF_RF.findall(lineas[0])

    pertenencia: dict[str, list[str]] = {}
    for grupo, refs in grupos.items():
        for ref in refs:
            pertenencia.setdefault(ref, []).append(grupo)

    for rf in sorted(ids_rf):
        if rf not in pertenencia:
            errores.append(f"{rf} no está clasificado.")
    for rf, gs in sorted(pertenencia.items()):
        if len(gs) > 1:
            errores.append(f"{rf} está clasificado en más de un grupo ({', '.join(gs)}).")
        if rf not in ids_rf:
            errores.append(f"{rf} está clasificado pero no está definido en la tabla de RF.")

    n_imp = len(set(grupos.get("Imprescindible", [])))
    if n_imp > MAX_IMPRESCINDIBLES:
        errores.append(f"Hay {n_imp} RF imprescindibles; el máximo es {MAX_IMPRESCINDIBLES}.")
    if "Imprescindible" in grupos and n_imp == 0 and not any("Imprescindible" in e for e in errores):
        errores.append("No hay RF imprescindibles.")
    return errores


def verificar_diagrama(cuerpos: dict[int, str], raiz: Path) -> list[str]:
    errores = []
    ruta = raiz / RUTA_DIAGRAMA
    if not ruta.is_file():
        errores.append(f"No existe el diagrama {RUTA_DIAGRAMA}.")
    else:
        with ruta.open("rb") as f:
            if f.read(8) != FIRMA_PNG:
                errores.append(f"{RUTA_DIAGRAMA} no es un PNG válido.")
    if REFERENCIA_DIAGRAMA not in cuerpos.get(3, ""):
        errores.append(f"La sección 3 no contiene la referencia literal '{REFERENCIA_DIAGRAMA}'.")
    return errores


def verificar(texto: str, raiz: Path = RAIZ) -> list[str]:
    """Devuelve la lista de errores de la ficha (vacía si cumple)."""
    cuerpos, errores = separar_secciones(texto)
    errores += verificar_secciones_completas(cuerpos)
    errores += verificar_pendientes(cuerpos)
    errores += verificar_problema_sin_tecnologia(cuerpos)
    errores += verificar_requerimientos(cuerpos)
    errores += verificar_diagrama(cuerpos, raiz)
    return errores


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ficha", type=Path, default=FICHA_POR_DEFECTO)
    parser.add_argument("--raiz", type=Path, default=RAIZ)
    args = parser.parse_args(argv)

    if not args.ficha.is_file():
        print(f"ERROR: no existe la ficha {args.ficha}")
        return 1
    errores = verificar(args.ficha.read_text(encoding="utf-8"), args.raiz)
    if errores:
        print(f"La ficha NO cumple ({len(errores)} errores):")
        for e in errores:
            print(f"  - {e}")
        return 1
    print(MENSAJE_OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
