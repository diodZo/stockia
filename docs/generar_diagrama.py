"""Genera docs/diagrama_arquitectura.png (fuente editable del diagrama de StockIA).

Requiere Pillow (ya presente en el entorno de desarrollo; no forma parte de los
scripts del Bloque 33 que usan solo la librería estándar).

Uso:
    py docs/generar_diagrama.py

Los nombres FastAPI, Orquestación, Gemini, Chroma y Docker deben coincidir con
docs/ficha_diseno_funcional.md.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SALIDA = Path(__file__).resolve().parent / "diagrama_arquitectura.png"
ANCHO, ALTO = 1720, 1100

FUENTES = Path("C:/Windows/Fonts")


def fuente(tamano: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    candidatos = ["segoeuib.ttf", "arialbd.ttf"] if negrita else ["segoeui.ttf", "arial.ttf"]
    for nombre in candidatos:
        ruta = FUENTES / nombre
        if ruta.exists():
            return ImageFont.truetype(str(ruta), tamano)
    return ImageFont.load_default()


F_TITULO = fuente(30, True)
F_CAJA = fuente(21, True)
F_SUB = fuente(16)
F_FLECHA = fuente(15)
F_NOTA = fuente(15)

TINTA = (30, 41, 59)
GRIS = (100, 116, 139)
AZUL_DOCKER = (37, 99, 235)

img = Image.new("RGB", (ANCHO, ALTO), "white")
d = ImageDraw.Draw(img)


def caja(cx: int, cy: int, w: int, h: int, titulo: str, sub: str, relleno, borde=GRIS, punteada=False):
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    if punteada:
        d.rounded_rectangle((x0, y0, x1, y1), 14, fill=relleno)
        linea_punteada_rect(x0, y0, x1, y1, borde, 2, 10)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), 14, fill=relleno, outline=borde, width=2)
    lineas = [(titulo, F_CAJA, TINTA)] + [(s, F_SUB, (51, 65, 85)) for s in sub.split("\n") if s]
    alturas = [d.textbbox((0, 0), t, font=f)[3] for t, f, _ in lineas]
    total = sum(alturas) + 6 * (len(lineas) - 1)
    y = cy - total // 2
    for (t, f, c), h_l in zip(lineas, alturas):
        d.text((cx, y), t, font=f, fill=c, anchor="ma")
        y += h_l + 6
    return x0, y0, x1, y1


def segmento_punteado(p, q, color, ancho, paso):
    largo = math.dist(p, q)
    if largo == 0:
        return
    n = int(largo // paso)
    for i in range(0, n, 2):
        a = i / n
        b = min((i + 1) / n, 1)
        d.line(
            (p[0] + (q[0] - p[0]) * a, p[1] + (q[1] - p[1]) * a,
             p[0] + (q[0] - p[0]) * b, p[1] + (q[1] - p[1]) * b),
            fill=color, width=ancho,
        )


def linea_punteada_rect(x0, y0, x1, y1, color, ancho, paso):
    for p, q in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        segmento_punteado(p, q, color, ancho, paso)


def punta(p_origen, p_fin, color):
    ang = math.atan2(p_fin[1] - p_origen[1], p_fin[0] - p_origen[0])
    largo, abre = 14, math.radians(26)
    a = (p_fin[0] - largo * math.cos(ang - abre), p_fin[1] - largo * math.sin(ang - abre))
    b = (p_fin[0] - largo * math.cos(ang + abre), p_fin[1] - largo * math.sin(ang + abre))
    d.polygon([p_fin, a, b], fill=color)


def flecha_doble(p, q, color=TINTA):
    d.line((*p, *q), fill=color, width=3)
    punta(p, q, color)
    punta(q, p, color)


def etiqueta(x, y, lineas, alinear="la"):
    for i, t in enumerate(lineas):
        d.text((x, y + i * 20), t, font=F_FLECHA, fill=TINTA, anchor=alinear)


# Título
d.text((ANCHO // 2, 24), "StockIA — Arquitectura del MVP (Bloque 33)", font=F_TITULO, fill=TINTA, anchor="ma")

# Frontera Docker
DX0, DY0, DX1, DY1 = 380, 255, 1150, 965
linea_punteada_rect(DX0, DY0, DX1, DY1, AZUL_DOCKER, 3, 12)
d.text((DX1 - 16, DY1 - 40), "Docker — contenedor del servicio StockIA", font=F_CAJA, fill=AZUL_DOCKER, anchor="ra")

# Bloques principales (7) + frontera Docker
cliente = caja(780, 120, 320, 74, "Cliente / Vendedora", "navegador o cliente HTTP", (226, 232, 240))
fastapi = caja(780, 335, 380, 84, "FastAPI", "endpoint REST POST /consulta", (219, 234, 254))
orq = caja(780, 480, 420, 96, "Orquestación", "herramientas autorizadas · trace ID\nabstención si faltan datos", (224, 231, 255))
gemini = caja(1570, 480, 260, 96, "Gemini", "modelo vía API externa\n(clave en variable de entorno)", (254, 243, 199))
conect = caja(620, 690, 330, 90, "Capa de conectores", "adaptadores de solo lectura", (220, 252, 231))
chroma = caja(980, 690, 300, 90, "Chroma", "documentación técnica (opcional)", (243, 232, 255))
sqlite = caja(620, 860, 330, 84, "SQLite", "inventario simulado (datos ficticios)", (220, 252, 231))

# Extensión futura (anotación, no es bloque del MVP)
php = caja(185, 860, 300, 100, "Extensión futura", "adaptador HTTP → PHP\nGL Repuestos (fuera del MVP)", (248, 250, 252), GRIS, punteada=True)

# Flechas con nombres de datos
flecha_doble((780, cliente[3]), (780, fastapi[1]))
etiqueta(796, 172, ["↓ pregunta (JSON)", "↑ producto, cantidad, fuente,", "   trace ID y estado (JSON)"])

flecha_doble((780, fastapi[3]), (780, orq[1]))
etiqueta(796, 386, ["↓ pregunta validada + trace ID", "↑ respuesta estructurada o abstención"])

flecha_doble((orq[2], 480), (gemini[0], 480))
etiqueta(1162, 432, ["→ pregunta + contexto", "   autorizado"], "la")
etiqueta(1162, 492, ["← herramienta elegida", "   / redacción"], "la")

flecha_doble((640, orq[3]), (640, conect[1]))
etiqueta(628, 560, ["↓ consulta parametrizada", "   (SKU / nombre)", "↑ producto + existencias + fuente"], "ra")

flecha_doble((900, orq[3]), (900, chroma[1]))
etiqueta(914, 560, ["↓ consulta de compatibilidad", "↑ fragmentos + fuente"])

flecha_doble((620, conect[3]), (620, sqlite[1]))
etiqueta(636, 750, ["↓ SELECT predefinido (solo lectura)", "↑ filas de inventario ficticio"])

# Conector futuro: línea discontinua gris desde la capa de conectores
segmento_punteado((conect[0], 690), (185, 690), GRIS, 2, 8)
segmento_punteado((185, 690), (185, php[1]), GRIS, 2, 8)
punta((185, 690), (185, php[1]), GRIS)
d.text((200, 702), "consulta HTTP futura", font=F_FLECHA, fill=GRIS)
d.text((200, 722), "(no MVP)", font=F_FLECHA, fill=GRIS)

# Leyenda y reglas
ly = 995
d.line((60, ly + 10, 110, ly + 10), fill=TINTA, width=3)
d.text((120, ly), "Flujo implementable en el MVP", font=F_NOTA, fill=TINTA)
segmento_punteado((420, ly + 10), (470, ly + 10), GRIS, 2, 8)
d.text((480, ly), "Extensión futura, fuera del MVP", font=F_NOTA, fill=GRIS)
segmento_punteado((790, ly + 10), (840, ly + 10), AZUL_DOCKER, 3, 12)
d.text((850, ly), "Frontera del contenedor Docker", font=F_NOTA, fill=AZUL_DOCKER)
d.text(
    (60, ly + 40),
    "Reglas: sin SQL arbitrario generado por la IA · sin modificación de inventario · "
    "las existencias vienen siempre del origen autorizado · se permite abstención",
    font=F_NOTA, fill=TINTA,
)

img.save(SALIDA)
print(f"Diagrama generado: {SALIDA}")
