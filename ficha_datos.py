"""Lectura estructurada de la ficha de diseño funcional de StockIA (Bloque 34).

Convierte docs/ficha_diseno_funcional.md y docs/revision_alcance.md en datos
(requerimientos, clasificación, criterios de aceptación, hitos, datos de prueba
y registro de revisión) que usan resumen_ficha.py y verificar_ficha_completa.py.

Este módulo solo lee y estructura; no decide si la ficha cumple.
Reutiliza el separador de secciones de verificar_ficha.py (Bloque 33).
Solo usa la librería estándar (Python 3.10+).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import verificar_ficha as vf

RAIZ = vf.RAIZ
FICHA_POR_DEFECTO = vf.FICHA_POR_DEFECTO
REVISION_POR_DEFECTO = RAIZ / "docs" / "revision_alcance.md"

GRUPOS = vf.GRUPOS  # ("Imprescindible", "Deseable", "Fuera de alcance")

RE_REF_REQ = re.compile(r"\bRN?F-\d{2}\b")
RE_REF_CA = re.compile(r"\bCA-\d{2}\b")
RE_SKU = re.compile(r"\bDEMO-\d{3}\b")

# Formato del curso: "- CA-01 (RF-01): descripción" (se admiten varias referencias).
# [ \t] y no \s: \s cruzaría saltos de línea y absorbería líneas en blanco previas.
RE_CA_CANDIDATA = re.compile(r"^[ \t]*[-*][ \t]*CA\b.*$", re.MULTILINE)
RE_CA = re.compile(r"^- (CA-\d{2}) \((RN?F-\d{2}(?:, RN?F-\d{2})*)\): (\S.*)$")

# Formato del curso: "- H1 (3 h): Descripción. Cubre: RF-01. Se comprueba con: CA-01."
RE_HITO_CANDIDATA = re.compile(r"^[ \t]*[-*][ \t]*H\d.*$", re.MULTILINE)
RE_HITO = re.compile(
    r"^- (H\d+) \((\d+(?:[.,]\d+)?) h\): (.+?) Cubre: ([^.]*)\. Se comprueba con: ([^.]*)\.\s*$"
)

RE_PRODUCTO = re.compile(
    r"^\|\s*(DEMO-\d{3})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*$", re.MULTILINE
)


@dataclass(frozen=True)
class Criterio:
    id: str
    refs: tuple[str, ...]
    texto: str


@dataclass(frozen=True)
class Hito:
    id: str
    horas: float
    descripcion: str
    cubre: tuple[str, ...]
    criterios: tuple[str, ...]


@dataclass(frozen=True)
class Producto:
    sku: str
    nombre: str
    descripcion: str
    existencias: int


@dataclass
class Ficha:
    cuerpos: dict[int, str]
    errores_estructura: list[str]
    rf: list[str] = field(default_factory=list)
    rnf: list[tuple[str, str]] = field(default_factory=list)  # (id, resto de la fila)
    clasificacion: dict[str, list[str]] = field(default_factory=dict)
    criterios: list[Criterio] = field(default_factory=list)
    criterios_mal_formados: list[str] = field(default_factory=list)
    hitos: list[Hito] = field(default_factory=list)
    hitos_mal_formados: list[str] = field(default_factory=list)
    productos: list[Producto] = field(default_factory=list)

    # --- Conjuntos derivados ---------------------------------------------
    @property
    def ids_rf(self) -> set[str]:
        return set(self.rf)

    @property
    def ids_rnf(self) -> set[str]:
        return {i for i, _ in self.rnf}

    @property
    def ids_requerimientos(self) -> set[str]:
        return self.ids_rf | self.ids_rnf

    @property
    def imprescindibles(self) -> list[str]:
        return self.clasificacion.get("Imprescindible", [])

    @property
    def ids_criterios(self) -> list[str]:
        return [c.id for c in self.criterios]

    # --- Cobertura -----------------------------------------------------------
    def criterios_de(self, req: str) -> list[str]:
        return [c.id for c in self.criterios if req in c.refs]

    @property
    def imprescindibles_sin_criterio(self) -> list[str]:
        return [r for r in self.imprescindibles if not self.criterios_de(r)]

    @property
    def rnf_sin_criterio(self) -> list[str]:
        return [r for r, _ in self.rnf if not self.criterios_de(r)]

    @property
    def criterios_sin_hito(self) -> list[str]:
        cubiertos = {c for h in self.hitos for c in h.criterios}
        return [c for c in self.ids_criterios if c not in cubiertos]

    @property
    def hitos_sin_criterio(self) -> list[str]:
        return [h.id for h in self.hitos if not h.criterios]

    @property
    def horas_planificadas(self) -> float:
        return round(sum(h.horas for h in self.hitos), 2)

    def hitos_de(self, criterio: str) -> list[str]:
        return [h.id for h in self.hitos if criterio in h.criterios]

    def producto(self, sku: str) -> Producto | None:
        return next((p for p in self.productos if p.sku == sku), None)


def _numero(texto: str) -> float:
    return float(texto.replace(",", "."))


def _clasificacion(cuerpo2: str) -> dict[str, list[str]]:
    grupos: dict[str, list[str]] = {}
    for grupo in GRUPOS:
        refs: list[str] = []
        for linea in re.findall(rf"^{re.escape(grupo)}:(.*)$", cuerpo2, re.MULTILINE):
            refs += vf.RE_REF_RF.findall(linea)
        grupos[grupo] = refs
    return grupos


def _criterios(cuerpo4: str) -> tuple[list[Criterio], list[str]]:
    criterios, mal = [], []
    for m in RE_CA_CANDIDATA.finditer(cuerpo4):
        linea = m.group(0).rstrip()
        mc = RE_CA.match(linea)
        if mc:
            refs = tuple(r.strip() for r in mc.group(2).split(","))
            criterios.append(Criterio(mc.group(1), refs, mc.group(3)))
        else:
            mal.append(linea.strip())
    return criterios, mal


def _hitos(cuerpo5: str) -> tuple[list[Hito], list[str]]:
    hitos, mal = [], []
    for m in RE_HITO_CANDIDATA.finditer(cuerpo5):
        linea = m.group(0).rstrip()
        mh = RE_HITO.match(linea)
        if mh:
            hitos.append(Hito(
                id=mh.group(1),
                horas=_numero(mh.group(2)),
                descripcion=mh.group(3).strip(),
                cubre=tuple(RE_REF_REQ.findall(mh.group(4))),
                criterios=tuple(RE_REF_CA.findall(mh.group(5))),
            ))
        else:
            mal.append(linea.strip())
    return hitos, mal


def cargar_ficha(texto: str) -> Ficha:
    cuerpos, errores = vf.separar_secciones(texto)
    ficha = Ficha(cuerpos=cuerpos, errores_estructura=errores)
    cuerpo2 = cuerpos.get(2, "")
    ficha.rf = vf.RE_FILA_RF.findall(cuerpo2)
    ficha.rnf = vf.RE_FILA_RNF.findall(cuerpo2)
    ficha.clasificacion = _clasificacion(cuerpo2)
    ficha.criterios, ficha.criterios_mal_formados = _criterios(cuerpos.get(4, ""))
    ficha.hitos, ficha.hitos_mal_formados = _hitos(cuerpos.get(5, ""))
    ficha.productos = [
        Producto(s, n.strip(), d.strip(), int(e)) for s, n, d, e in RE_PRODUCTO.findall(cuerpos.get(4, ""))
    ]
    return ficha


def leer_ficha(ruta: Path = FICHA_POR_DEFECTO) -> Ficha:
    return cargar_ficha(Path(ruta).read_text(encoding="utf-8"))


# --- Registro de revisión cruzada ------------------------------------------

RE_CAMPO = re.compile(r"^- ([^:\n]+): ?(.*)$", re.MULTILINE)
RE_HALLAZGO = re.compile(r"^- Hallazgo (\d+): ?(.*)$")
# Exactamente dos espacios antes de "Decisión:".
RE_DECISION = re.compile(r"^  (?! )Decisión: (aceptado|rechazado|aplazado)\. (Cambio|Justificación): (\S.*)$")


@dataclass(frozen=True)
class Hallazgo:
    numero: int
    descripcion: str
    linea_decision: str | None
    decision: str | None = None
    tipo_detalle: str | None = None  # "Cambio" o "Justificación"
    detalle: str | None = None


@dataclass
class Revision:
    texto: str
    campos: dict[str, str]
    hallazgos: list[Hallazgo]
    aciertos: list[str]


RE_BLOQUE_CODIGO = re.compile(r"^```.*?^```[^\n]*$", re.MULTILINE | re.DOTALL)


def cargar_revision(texto: str) -> Revision:
    """Lee el registro; ignora bloques de código (ejemplos de formato)."""
    original = texto
    texto = RE_BLOQUE_CODIGO.sub("", texto)
    campos = {}
    for m in RE_CAMPO.finditer(texto):
        clave = m.group(1).strip()
        if not clave.startswith("Hallazgo") and clave != "Acierto":
            campos.setdefault(clave, m.group(2).strip())
    lineas = texto.splitlines()
    hallazgos = []
    for i, linea in enumerate(lineas):
        mh = RE_HALLAZGO.match(linea)
        if not mh:
            continue
        siguiente = lineas[i + 1] if i + 1 < len(lineas) else None
        md = RE_DECISION.match(siguiente) if siguiente is not None else None
        hallazgos.append(Hallazgo(
            numero=int(mh.group(1)),
            descripcion=mh.group(2).strip(),
            linea_decision=siguiente,
            decision=md.group(1) if md else None,
            tipo_detalle=md.group(2) if md else None,
            detalle=md.group(3).strip() if md else None,
        ))
    aciertos = [m.group(1).strip() for m in re.finditer(r"^- Acierto: ?(.*)$", texto, re.MULTILINE)]
    return Revision(texto=original, campos=campos, hallazgos=hallazgos, aciertos=aciertos)


def leer_revision(ruta: Path = REVISION_POR_DEFECTO) -> Revision | None:
    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    return cargar_revision(ruta.read_text(encoding="utf-8"))
