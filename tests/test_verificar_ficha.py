"""Pruebas de verificar_ficha.py, incluidas pruebas negativas (solo librería estándar)."""

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import verificar_ficha as vf  # noqa: E402

FICHA_REAL = (RAIZ / "docs" / "ficha_diseno_funcional.md").read_text(encoding="utf-8")


class BaseFicha(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        (self.raiz / "docs").mkdir()
        shutil.copy(RAIZ / vf.RUTA_DIAGRAMA, self.raiz / vf.RUTA_DIAGRAMA)

    def tearDown(self):
        self._tmp.cleanup()

    def errores(self, texto):
        return vf.verificar(texto, self.raiz)

    def assertError(self, texto, fragmento):
        errores = self.errores(texto)
        self.assertTrue(any(fragmento in e for e in errores),
                        f"Se esperaba un error con '{fragmento}', se obtuvo: {errores}")


class TestFichaValida(BaseFicha):
    def test_ficha_real_cumple(self):
        self.assertEqual(self.errores(FICHA_REAL), [])

    def test_ficha_del_repositorio_con_diagrama_real(self):
        self.assertEqual(vf.verificar(FICHA_REAL, RAIZ), [])


class TestFichaNegativa(BaseFicha):
    def test_ficha_vacia(self):
        errores = self.errores("")
        self.assertEqual(sum("Falta la sección" in e for e in errores), 5)

    def test_ficha_incompleta_con_completar(self):
        texto = FICHA_REAL.replace("**Quién tiene el problema.**", "[COMPLETAR] **Quién tiene el problema.**")
        self.assertError(texto, "La sección 1 contiene [COMPLETAR]")

    def test_seccion_3_pendiente(self):
        inicio = FICHA_REAL.index("## 3. Arquitectura de la solución")
        fin = FICHA_REAL.index("## 4. Criterios de aceptación")
        texto = FICHA_REAL[:inicio] + "## 3. Arquitectura de la solución\n\n" + vf.MARCA_PENDIENTE + "\n\n" + FICHA_REAL[fin:]
        self.assertError(texto, "La sección 3 está marcada como pendiente")

    def test_encabezado_mal_titulado(self):
        texto = FICHA_REAL.replace("## 1. Problema de negocio", "## 1. Problema")
        self.assertError(texto, "La sección 1 debe titularse")

    def test_seccion_faltante(self):
        texto = FICHA_REAL.replace("## 5. Plan de construcción por hitos", "## Plan")
        self.assertError(texto, "Falta la sección '## 5.")

    def _con_secciones_4_5_pendientes(self):
        inicio = FICHA_REAL.index("## 4. Criterios de aceptación")
        return (FICHA_REAL[:inicio]
                + "## 4. Criterios de aceptación\n\n" + vf.MARCA_PENDIENTE + "\n\n"
                + "## 5. Plan de construcción por hitos\n\n" + vf.MARCA_PENDIENTE + "\n")

    def test_secciones_4_5_pendientes_compatibles_con_bloque_33(self):
        self.assertEqual(self.errores(self._con_secciones_4_5_pendientes()), [])

    def test_seccion_4_mezcla_pendiente_y_contenido(self):
        texto = FICHA_REAL.replace("## 4. Criterios de aceptación\n",
                                   "## 4. Criterios de aceptación\n\n" + vf.MARCA_PENDIENTE + "\n", 1)
        self.assertError(texto, "La sección 4 mezcla la marca")

    def test_seccion_5_con_completar(self):
        texto = FICHA_REAL.replace("Total planificado:", "[COMPLETAR] Total planificado:")
        self.assertError(texto, "La sección 5 contiene [COMPLETAR]")

    def test_rf_duplicado(self):
        texto = FICHA_REAL.replace("| RF-03 |", "| RF-02 |", 1)
        self.assertError(texto, "Identificadores RF duplicados: RF-02")

    def test_rf_formato_invalido(self):
        texto = FICHA_REAL.replace("| RF-08 |", "| RF-8 |")
        self.assertError(texto, "formato inválido")

    def test_diagrama_inexistente(self):
        (self.raiz / vf.RUTA_DIAGRAMA).unlink()
        self.assertError(FICHA_REAL, "No existe el diagrama")

    def test_diagrama_no_png(self):
        (self.raiz / vf.RUTA_DIAGRAMA).write_bytes(b"no es una imagen")
        self.assertError(FICHA_REAL, "no es un PNG válido")

    def test_sin_referencia_al_diagrama(self):
        texto = FICHA_REAL.replace(vf.REFERENCIA_DIAGRAMA, "Diagrama: ver carpeta docs")
        self.assertError(texto, "referencia literal")

    def test_seccion_1_con_tecnologia(self):
        texto = FICHA_REAL.replace("**Qué mejora se espera.**",
                                   "**Qué mejora se espera.** Un chatbot con Gemini y RAG.")
        errores = self.errores(texto)
        mensaje = next(e for e in errores if "sección 1 menciona" in e)
        for termino in ("chatbot", "Gemini", "RAG"):
            self.assertIn(termino, mensaje)

    def test_seccion_1_con_ia_y_api(self):
        texto = FICHA_REAL.replace("**Qué sucede.**", "**Qué sucede.** Se necesita IA vía API.")
        self.assertError(texto, "sección 1 menciona")

    def test_palabras_comunes_no_disparan_falsos_positivos(self):
        cuerpos = {1: "La media de días con consultas diarias es alta; se apilan las dudas."}
        self.assertEqual(vf.verificar_problema_sin_tecnologia(cuerpos), [])

    def test_rnf_sin_numero(self):
        texto = FICHA_REAL.replace(
            "| RNF-05 | Trazabilidad | 20 de 20 consultas de prueba (100 %) devuelven trace ID y estado. |",
            "| RNF-05 | Trazabilidad | Todas las consultas devuelven trace ID y estado. |",
        )
        self.assertNotEqual(texto, FICHA_REAL)
        self.assertError(texto, "RNF-05 no tiene un valor numérico medible")

    def test_rf_en_dos_grupos(self):
        texto = FICHA_REAL.replace("Deseable: RF-05, RF-06", "Deseable: RF-04, RF-05, RF-06")
        self.assertError(texto, "RF-04 está clasificado en más de un grupo")

    def test_rf_sin_clasificar(self):
        texto = FICHA_REAL.replace("Fuera de alcance: RF-07, RF-08", "Fuera de alcance: RF-07")
        self.assertError(texto, "RF-08 no está clasificado")

    def test_rf_clasificado_no_definido(self):
        texto = FICHA_REAL.replace("Fuera de alcance: RF-07, RF-08", "Fuera de alcance: RF-07, RF-08, RF-09")
        self.assertError(texto, "RF-09 está clasificado pero no está definido")

    def test_mas_de_cinco_imprescindibles(self):
        texto = (FICHA_REAL
                 .replace("Imprescindible: RF-01, RF-02, RF-03, RF-04",
                          "Imprescindible: RF-01, RF-02, RF-03, RF-04, RF-05, RF-06")
                 .replace("Deseable: RF-05, RF-06", "Deseable:"))
        self.assertError(texto, "Hay 6 RF imprescindibles; el máximo es 5")


class TestCLI(BaseFicha):
    def run_main(self, args):
        with redirect_stdout(io.StringIO()):
            return vf.main(args)

    def test_cli_ok(self):
        self.assertEqual(self.run_main(["--raiz", str(RAIZ)]), 0)

    def test_cli_falla_con_ficha_inexistente(self):
        self.assertEqual(self.run_main(["--ficha", str(self.raiz / "no_existe.md")]), 1)

    def test_cli_falla_con_errores(self):
        ficha = self.raiz / "ficha.md"
        ficha.write_text(FICHA_REAL.replace("| RF-03 |", "| RF-02 |", 1), encoding="utf-8")
        self.assertEqual(self.run_main(["--ficha", str(ficha), "--raiz", str(self.raiz)]), 1)


if __name__ == "__main__":
    unittest.main()
