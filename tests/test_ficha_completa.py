"""Pruebas del Bloque 34: ficha_datos.py, resumen_ficha.py y verificar_ficha_completa.py.

Incluyen casos positivos y negativos. Solo librería estándar.
Los registros de revisión "válidos" de este archivo son datos de prueba sintéticos
(revisora "Persona Ficticia"), no una revisión real del proyecto.
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import ficha_datos as fd  # noqa: E402
import resumen_ficha as rf  # noqa: E402
import verificar_ficha as vf  # noqa: E402
import verificar_ficha_completa as vfc  # noqa: E402

FICHA_REAL = (RAIZ / "docs" / "ficha_diseno_funcional.md").read_text(encoding="utf-8")
HOY = date(2026, 12, 1)

REVISION_SINTETICA = """# Registro de revisión (dato de prueba)

- Revisor: Persona Ficticia (dato de prueba)
- Tipo de revisión: revisión cruzada
- Fecha de revisión: 2026-11-28
- Fecha de término de la ficha: 2026-11-27
- Versión revisada: commit de prueba

## Hallazgos

- Hallazgo 1: CA-14 no define el entorno de prueba.
  Decisión: aceptado. Cambio: se documenta el entorno en el README.
- Hallazgo 2: Faltan casos de SKU con minúsculas.
  Decisión: aplazado. Justificación: se evaluará en H2.

## Acierto identificado

- Acierto: los datos de prueba ficticios hacen reproducibles los criterios.
"""


def errores_de(funcion, texto):
    return funcion(fd.cargar_ficha(texto))


def contiene(errores, fragmento):
    return any(fragmento in e for e in errores)


def todas_las_comprobaciones(texto):
    return [e for _, errores in vfc.comprobaciones_ficha(texto, RAIZ) for e in errores]


class TestLecturaFicha(unittest.TestCase):
    def setUp(self):
        self.ficha = fd.cargar_ficha(FICHA_REAL)

    def test_requerimientos_conservan_identificadores(self):
        self.assertEqual(self.ficha.rf, [f"RF-0{i}" for i in range(1, 9)])
        self.assertEqual([i for i, _ in self.ficha.rnf], [f"RNF-0{i}" for i in range(1, 6)])

    def test_clasificacion(self):
        self.assertEqual(self.ficha.imprescindibles, ["RF-01", "RF-02", "RF-03", "RF-04"])
        self.assertEqual(self.ficha.clasificacion["Deseable"], ["RF-05", "RF-06"])
        self.assertEqual(self.ficha.clasificacion["Fuera de alcance"], ["RF-07", "RF-08"])

    def test_criterios_parseados(self):
        self.assertEqual(self.ficha.criterios_mal_formados, [])
        self.assertEqual(self.ficha.ids_criterios[0], "CA-01")
        ca07 = next(c for c in self.ficha.criterios if c.id == "CA-07")
        self.assertEqual(ca07.refs, ("RF-02", "RF-04"))

    def test_hitos_parseados_con_decimales_con_coma(self):
        horas = {h.id: h.horas for h in self.ficha.hitos}
        self.assertEqual(horas, {"H1": 3, "H2": 1.5, "H3": 2, "H4": 3.5, "H5": 6})
        self.assertEqual(self.ficha.horas_planificadas, 16)

    def test_datos_de_prueba(self):
        self.assertEqual(len(self.ficha.productos), 20)
        self.assertEqual(self.ficha.producto("DEMO-002").existencias, 0)
        self.assertIsNone(self.ficha.producto("DEMO-999"))

    def test_criterio_mal_formado_se_detecta(self):
        ficha = fd.cargar_ficha(FICHA_REAL.replace("- CA-04 (RF-02):", "- CA-04 RF-02:"))
        self.assertEqual(len(ficha.criterios_mal_formados), 1)

    def test_hito_mal_formado_se_detecta(self):
        ficha = fd.cargar_ficha(FICHA_REAL.replace("Cubre: RF-02. Se comprueba con:", "Cubre RF-02, se comprueba con:"))
        self.assertEqual(len(ficha.hitos_mal_formados), 1)


class TestFichaRealCompleta(unittest.TestCase):
    def test_ficha_real_pasa_todas_las_comprobaciones_automaticas(self):
        self.assertEqual(todas_las_comprobaciones(FICHA_REAL), [])

    def test_ficha_real_cubre_los_siete_casos(self):
        casos = vfc.detectar_casos(fd.cargar_ficha(FICHA_REAL))
        self.assertEqual(len(casos), 7)
        for caso, cas in casos.items():
            self.assertTrue(cas, caso)
        self.assertIn("CA-05", casos["Búsqueda por descripción"])
        self.assertIn("CA-09", casos["Producto sin existencias"])


class TestCobertura(unittest.TestCase):
    def test_imprescindible_sin_criterio(self):
        texto = (FICHA_REAL.replace("- CA-08 (RF-03):", "- CA-08 (RF-05):")
                 .replace("- CA-09 (RF-03, RF-04):", "- CA-09 (RF-04):")
                 .replace("- CA-10 (RF-03):", "- CA-10 (RF-05):"))
        self.assertTrue(contiene(errores_de(vfc.verificar_cobertura, texto), "imprescindible RF-03"))

    def test_rnf_sin_criterio(self):
        texto = FICHA_REAL.replace("- CA-16 (RNF-03):", "- CA-16 (RF-04):")
        self.assertTrue(contiene(errores_de(vfc.verificar_cobertura, texto), "no funcional RNF-03"))


class TestCriterios(unittest.TestCase):
    def test_criterio_duplicado(self):
        texto = FICHA_REAL.replace("- CA-05 (RF-02):", "- CA-04 (RF-02):")
        self.assertTrue(contiene(errores_de(vfc.verificar_criterios, texto), "Criterios duplicados: CA-04"))

    def test_referencia_inexistente(self):
        texto = FICHA_REAL.replace("- CA-04 (RF-02):", "- CA-04 (RF-09):")
        self.assertTrue(contiene(errores_de(vfc.verificar_criterios, texto), "inexistentes: RF-09"))

    def test_mal_formado(self):
        texto = FICHA_REAL.replace("- CA-04 (RF-02):", "- CA-4 (RF-02):")
        self.assertTrue(contiene(errores_de(vfc.verificar_criterios, texto), "Criterio mal formado"))

    def test_expresion_vaga(self):
        texto = FICHA_REAL.replace("- CA-06 (RF-02): Búsqueda por nombre:",
                                   "- CA-06 (RF-02): La búsqueda funciona correctamente:")
        self.assertTrue(contiene(errores_de(vfc.verificar_criterios, texto), "expresiones vagas"))

    def test_criterio_sin_valor_observable(self):
        texto = FICHA_REAL.replace("- CA-19 (RNF-05):", "- CA-20 (RNF-05): La consulta es buena.\n- CA-19 (RNF-05):")
        self.assertTrue(contiene(errores_de(vfc.verificar_criterios, texto), "CA-20 no tiene un valor observable"))

    def test_declarar_criterios_cumplidos(self):
        texto = FICHA_REAL.replace("Los criterios son objetivos", "Los criterios están cumplidos y son objetivos")
        self.assertTrue(contiene(errores_de(vfc.verificar_criterios, texto), "ya cumplidos"))

    def test_sin_criterios(self):
        texto = FICHA_REAL.replace("- CA-", "* criterio CA-")
        errores = errores_de(vfc.verificar_criterios, texto)
        self.assertTrue(contiene(errores, "No hay criterios de aceptación"))


class TestDatosYCasosNegativos(unittest.TestCase):
    def test_cantidad_citada_distinta_de_los_datos(self):
        texto = FICHA_REAL.replace('`producto.sku = "DEMO-003"` y `cantidad = 5`',
                                   '`producto.sku = "DEMO-003"` y `cantidad = 9`')
        self.assertNotEqual(texto, FICHA_REAL)
        self.assertTrue(contiene(errores_de(vfc.verificar_datos_prueba, texto), "cantidad = 9 para DEMO-003"))

    def test_nombre_citado_distinto(self):
        texto = FICHA_REAL.replace('`producto.nombre = "Bujía estándar BJ-8"`', '`producto.nombre = "Bujía BJ-9"`')
        self.assertTrue(contiene(errores_de(vfc.verificar_datos_prueba, texto), "espera el nombre"))

    def test_abstencion_con_sku_existente(self):
        texto = FICHA_REAL.replace("del SKU DEMO-999?", "del SKU DEMO-010?")
        self.assertTrue(contiene(errores_de(vfc.verificar_datos_prueba, texto), "abstención para DEMO-010"))

    def test_menos_productos_que_casos_de_rnf02(self):
        texto = FICHA_REAL.replace("| DEMO-020 |", "| SIN-020 |")
        self.assertTrue(contiene(errores_de(vfc.verificar_datos_prueba, texto), "RNF-02 exige 20"))

    def test_falta_caso_por_descripcion(self):
        # Si la pregunta incluye el nombre del producto ya no es una búsqueda por descripción.
        texto = FICHA_REAL.replace("¿Tienen una cadena reforzada de 120 eslabones?",
                                   "¿Tienen Cadena de transmisión 428H reforzada de 120 eslabones?")
        self.assertTrue(contiene(errores_de(vfc.verificar_casos_negativos, texto), "Búsqueda por descripción"))

    def test_falta_caso_sin_existencias(self):
        texto = FICHA_REAL.replace(
            "| Juego de pastillas orgánicas para freno de disco delantero | 0 |",
            "| Juego de pastillas orgánicas para freno de disco delantero | 3 |")
        errores = errores_de(vfc.verificar_casos_negativos, texto)
        self.assertTrue(contiene(errores, "Producto sin existencias"))

    def test_falta_caso_pregunta_invalida(self):
        texto = FICHA_REAL.replace("error_validacion", "rechazo")
        self.assertTrue(contiene(errores_de(vfc.verificar_casos_negativos, texto), "Pregunta vacía o inválida"))

    def test_falta_caso_sku_inexistente(self):
        texto = FICHA_REAL.replace("del SKU DEMO-999?", "del producto inexistente?")
        self.assertTrue(contiene(errores_de(vfc.verificar_casos_negativos, texto), "SKU inexistente"))


class TestHitos(unittest.TestCase):
    def test_criterio_sin_hito(self):
        texto = FICHA_REAL.replace(", CA-17.", ".").replace(", CA-17, CA-18,", ", CA-18,")
        self.assertTrue(contiene(errores_de(vfc.verificar_hitos, texto), "CA-17 no está asignado"))

    def test_hito_sin_criterios(self):
        texto = FICHA_REAL.replace("Se comprueba con: CA-04, CA-05, CA-06, CA-07.", "Se comprueba con: ninguno.")
        self.assertTrue(contiene(errores_de(vfc.verificar_hitos, texto), "El hito H2 no tiene criterios"))

    def test_hito_referencia_criterio_inexistente(self):
        texto = FICHA_REAL.replace("Se comprueba con: CA-04, CA-05", "Se comprueba con: CA-44, CA-05")
        self.assertTrue(contiene(errores_de(vfc.verificar_hitos, texto), "criterio inexistente CA-44"))

    def test_hito_declara_requerimiento_sin_evidencia(self):
        texto = FICHA_REAL.replace("Cubre: RF-02. Se comprueba", "Cubre: RF-02, RNF-04. Se comprueba")
        self.assertTrue(contiene(errores_de(vfc.verificar_hitos, texto), "H2 declara cubrir RNF-04"))

    def test_criterio_solo_en_hito_final(self):
        texto = FICHA_REAL.replace("Se comprueba con: CA-01, CA-02, CA-03, CA-18, CA-19.",
                                   "Se comprueba con: CA-01, CA-02, CA-03, CA-18.")
        self.assertTrue(contiene(errores_de(vfc.verificar_hitos, texto), "CA-19 solo se comprueba en el hito final"))


class TestPresupuesto(unittest.TestCase):
    def test_presupuesto_real(self):
        self.assertEqual(errores_de(vfc.verificar_presupuesto, FICHA_REAL), [])

    def test_presupuesto_excedido(self):
        texto = FICHA_REAL.replace("- H2 (1,5 h):", "- H2 (4 h):")
        errores = errores_de(vfc.verificar_presupuesto, texto)
        self.assertTrue(contiene(errores, "Presupuesto excedido"))
        self.assertTrue(contiene(errores, "Los hitos de construcción suman"))

    def test_reduccion_artificial_de_estimacion(self):
        texto = FICHA_REAL.replace("- H4 (3,5 h):", "- H4 (2 h):")
        self.assertTrue(contiene(errores_de(vfc.verificar_presupuesto, texto), "H4 tiene 2 h, menos que las 3.5 h"))

    def test_ultimo_hito_no_es_de_pruebas(self):
        texto = FICHA_REAL.replace("Pruebas de aceptación de todos los criterios, documentación, instalación limpia y preparación de la defensa.",
                                   "Ajustes finales.")
        self.assertTrue(contiene(errores_de(vfc.verificar_presupuesto, texto), "último hito"))


class TestMarcasPendientes(unittest.TestCase):
    def test_seccion_pendiente_bloque_34(self):
        inicio = FICHA_REAL.index("## 5. Plan de construcción por hitos")
        texto = FICHA_REAL[:inicio] + "## 5. Plan de construcción por hitos\n\n" + vf.MARCA_PENDIENTE + "\n"
        self.assertTrue(contiene(errores_de(lambda f: vfc.verificar_marcas(texto, f), texto), "La sección 5 sigue pendiente"))

    def test_marca_pendiente_del_bloque_33(self):
        texto = FICHA_REAL.replace("Total planificado:", "[PENDIENTE: se completa en el Bloque 33] Total planificado:")
        self.assertTrue(contiene(errores_de(lambda f: vfc.verificar_marcas(texto, f), texto), "[PENDIENTE"))


class TestRevision(unittest.TestCase):
    def verificar(self, texto):
        return vfc.verificar_revision(fd.cargar_revision(texto), hoy=HOY)

    def test_revision_sintetica_valida(self):
        self.assertEqual(self.verificar(REVISION_SINTETICA), [])

    def test_revision_ausente(self):
        self.assertTrue(contiene(vfc.verificar_revision(None, hoy=HOY), "Registro de revisión ausente"))

    def test_plantilla_del_repositorio_esta_pendiente(self):
        revision = fd.leer_revision(fd.REVISION_POR_DEFECTO)
        self.assertIsNotNone(revision)
        self.assertTrue(contiene(vfc.verificar_revision(revision, hoy=HOY), "PENDIENTE"))

    def test_ejemplo_en_bloque_de_codigo_no_cuenta(self):
        texto = REVISION_SINTETICA + "\n```text\n- Hallazgo 1: ejemplo\n  Decisión: aceptado. Cambio: x\n```\n"
        self.assertEqual(len(fd.cargar_revision(texto).hallazgos), 2)

    def test_decision_con_tres_espacios(self):
        texto = REVISION_SINTETICA.replace("  Decisión: aceptado.", "   Decisión: aceptado.")
        self.assertTrue(contiene(self.verificar(texto), "exactamente dos espacios"))

    def test_decision_no_valida(self):
        texto = REVISION_SINTETICA.replace("Decisión: aceptado.", "Decisión: quizás.")
        self.assertTrue(contiene(self.verificar(texto), "El hallazgo 1 no tiene"))

    def test_aplazado_sin_justificacion(self):
        texto = REVISION_SINTETICA.replace("aplazado. Justificación:", "aplazado. Cambio:")
        self.assertTrue(contiene(self.verificar(texto), "debe incluir 'Justificación'"))

    def test_aceptado_sin_cambio(self):
        texto = REVISION_SINTETICA.replace("aceptado. Cambio:", "aceptado. Justificación:")
        self.assertTrue(contiene(self.verificar(texto), "debe describir el 'Cambio'"))

    def test_un_solo_hallazgo(self):
        inicio = REVISION_SINTETICA.index("- Hallazgo 2:")
        fin = REVISION_SINTETICA.index("## Acierto")
        texto = REVISION_SINTETICA[:inicio] + "\n" + REVISION_SINTETICA[fin:]
        self.assertTrue(contiene(self.verificar(texto), "se requieren al menos 2"))

    def test_sin_acierto(self):
        texto = REVISION_SINTETICA.replace("- Acierto:", "Acierto:")
        self.assertTrue(contiene(self.verificar(texto), "ningún acierto"))

    def test_sin_revisor(self):
        texto = REVISION_SINTETICA.replace("- Revisor: Persona Ficticia (dato de prueba)", "- Revisor:")
        self.assertTrue(contiene(self.verificar(texto), "Falta el campo 'Revisor'"))

    def test_fecha_futura(self):
        texto = REVISION_SINTETICA.replace("2026-11-28", "2027-01-15")
        self.assertTrue(contiene(self.verificar(texto), "es futura"))

    def test_fecha_mal_formada(self):
        texto = REVISION_SINTETICA.replace("2026-11-28", "28/11/2026")
        self.assertTrue(contiene(self.verificar(texto), "no tiene formato AAAA-MM-DD"))

    def test_autorrevision_el_mismo_dia(self):
        texto = (REVISION_SINTETICA.replace("revisión cruzada", "autorrevisión")
                 .replace("Fecha de revisión: 2026-11-28", "Fecha de revisión: 2026-11-27"))
        self.assertTrue(contiene(self.verificar(texto), "al menos un día"))

    def test_autorrevision_al_dia_siguiente(self):
        texto = REVISION_SINTETICA.replace("revisión cruzada", "autorrevisión")
        self.assertEqual(self.verificar(texto), [])

    def test_tipo_no_valido(self):
        texto = REVISION_SINTETICA.replace("revisión cruzada", "revisión informal")
        self.assertTrue(contiene(self.verificar(texto), "Tipo de revisión no válido"))


class TestCLI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def ejecutar(self, modulo, args):
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = modulo.main(args)
        return codigo, salida.getvalue()

    def test_verificador_revision_pendiente_devuelve_2(self):
        codigo, salida = self.ejecutar(vfc, [])
        self.assertEqual(codigo, vfc.SALIDA_REVISION_PENDIENTE)
        self.assertIn("PENDIENTE", salida)
        self.assertIn("Requieren juicio humano", salida)

    def test_verificador_con_revision_completa_devuelve_0(self):
        revision = self.tmp / "revision.md"
        hoy = date.today()  # la CLI usa la fecha real: fechas sintéticas en el pasado
        texto = (REVISION_SINTETICA
                 .replace("2026-11-28", (hoy - timedelta(days=1)).isoformat())
                 .replace("2026-11-27", (hoy - timedelta(days=2)).isoformat()))
        revision.write_text(texto, encoding="utf-8")
        codigo, salida = self.ejecutar(vfc, ["--revision", str(revision)])
        self.assertEqual(codigo, vfc.SALIDA_OK, salida)

    def test_verificador_ficha_con_errores_devuelve_1(self):
        ficha = self.tmp / "ficha.md"
        ficha.write_text(FICHA_REAL.replace("- CA-05 (RF-02):", "- CA-04 (RF-02):"), encoding="utf-8")
        codigo, _ = self.ejecutar(vfc, ["--ficha", str(ficha)])
        self.assertEqual(codigo, vfc.SALIDA_ERRORES_FICHA)

    def test_verificador_ficha_inexistente(self):
        codigo, _ = self.ejecutar(vfc, ["--ficha", str(self.tmp / "no.md")])
        self.assertEqual(codigo, vfc.SALIDA_ERRORES_FICHA)

    def test_resumen(self):
        codigo, salida = self.ejecutar(rf, [])
        self.assertEqual(codigo, 0)
        for fragmento in ("(RF):     8", "(RNF): 5", "Imprescindibles:                     4",
                          "Criterios de aceptación:             19", "Hitos:                               5",
                          "16 h de 16 h máximo", "margen sin asignar: 4 h",
                          "Criterios sin hito:                  ninguno",
                          "Hitos sin criterio:                  ninguno"):
            self.assertIn(fragmento, salida)

    def test_resumen_informa_brechas(self):
        ficha = self.tmp / "ficha.md"
        ficha.write_text(FICHA_REAL.replace("- CA-16 (RNF-03):", "- CA-16 (RF-04):"), encoding="utf-8")
        codigo, salida = self.ejecutar(rf, ["--ficha", str(ficha)])
        self.assertEqual(codigo, 0)
        self.assertIn("RNF sin criterio:                    RNF-03", salida)

    def test_resumen_ficha_inexistente(self):
        codigo, _ = self.ejecutar(rf, ["--ficha", str(self.tmp / "no.md")])
        self.assertEqual(codigo, 1)


if __name__ == "__main__":
    unittest.main()
