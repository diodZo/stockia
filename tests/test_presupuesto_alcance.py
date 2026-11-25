"""Pruebas de presupuesto_alcance.py (solo librería estándar)."""

import io
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import presupuesto_alcance as pa  # noqa: E402


def tareas_sin(nombre: str) -> list[pa.Tarea]:
    return [t for t in pa.TAREAS_STOCKIA if t.nombre != nombre]


class TestPresupuesto(unittest.TestCase):
    def test_constantes_del_metodo(self):
        self.assertEqual(pa.HORAS_DISPONIBLES, 20)
        self.assertEqual(pa.FACTOR_NOVEDAD, 1.5)
        self.assertEqual(pa.RESERVA_PRUEBAS_DOCS, 0.30)
        self.assertEqual(pa.MARGEN_IMPREVISTOS, 0.20)

    def test_presupuesto_neto_es_10_horas(self):
        self.assertEqual(pa.presupuesto_neto(), 10)

    def test_presupuesto_invalido(self):
        with self.assertRaises(ValueError):
            pa.presupuesto_neto(0)
        with self.assertRaises(ValueError):
            pa.presupuesto_neto(20, 0.6, 0.5)

    def test_correccion_por_novedad(self):
        api = next(t for t in pa.TAREAS_STOCKIA if t.nombre == "API REST")
        self.assertEqual(api.horas_ajustadas, 3.0)
        sin_novedad = replace(api, novedad=False)
        self.assertEqual(sin_novedad.horas_ajustadas, 2.0)

    def test_horas_ajustadas_del_mvp(self):
        esperadas = {
            "API REST": 3,
            "Búsqueda de productos": 1.5,
            "Consulta de existencias": 2,
            "Respuesta con fuente y cantidad": 2,
            "Docker y configuración": 1.5,
        }
        reales = {t.nombre: t.horas_ajustadas for t in pa.TAREAS_STOCKIA if t.nombre in esperadas}
        self.assertEqual(reales, esperadas)
        self.assertEqual(sum(esperadas.values()), 10)


class TestPlanificacion(unittest.TestCase):
    def test_plan_real_es_viable_y_usa_10_horas(self):
        plan = pa.planificar(pa.TAREAS_STOCKIA, pa.presupuesto_neto())
        self.assertTrue(plan.es_viable)
        self.assertEqual(plan.horas_usadas, 10)
        self.assertEqual(plan.imprescindibles_fuera, [])
        self.assertEqual(plan.capas_faltantes, [])
        self.assertEqual(plan.rf_imprescindibles_sin_cubrir, [])
        self.assertTrue(all(t.prioridad == pa.IMPRESCINDIBLE for t in plan.dentro))

    def test_rechaza_sistemas_reales_aunque_sobren_horas(self):
        plan = pa.planificar(pa.TAREAS_STOCKIA, 100)
        fuera = {t.requerimientos[0]: motivo for t, motivo in plan.fuera}
        self.assertIn("RF-07", fuera)
        self.assertIn("RF-08", fuera)
        self.assertIn("sistemas", fuera["RF-07"])
        self.assertNotIn("RF-07", [r for t in plan.dentro for r in t.requerimientos])

    def test_deseable_con_sistema_real_tambien_se_rechaza(self):
        deseable_real = pa.Tarea("Conector PHP productivo", ("RF-06",), 1, pa.DESEABLE,
                                 pa.CAPA_INVENTARIO_IA, requiere_sistema_real=True)
        plan = pa.planificar([deseable_real], 100)
        self.assertEqual(plan.dentro, [])

    def test_prioriza_imprescindibles_sobre_deseables(self):
        deseables_primero = sorted(pa.TAREAS_STOCKIA, key=lambda t: t.prioridad != pa.DESEABLE)
        plan = pa.planificar(deseables_primero, 10)
        self.assertTrue(plan.es_viable)
        self.assertNotIn(pa.DESEABLE, {t.prioridad for t in plan.dentro})

    def test_detecta_imprescindible_fuera_por_falta_de_horas(self):
        plan = pa.planificar(pa.TAREAS_STOCKIA, 8)
        self.assertFalse(plan.es_viable)
        self.assertTrue(plan.imprescindibles_fuera)
        self.assertIn("MVP NO viable", pa.informe(plan))

    def test_total_que_cabe_sin_contenedor_no_es_viable(self):
        plan = pa.planificar(tareas_sin("Docker y configuración"), 10)
        self.assertLessEqual(plan.horas_usadas, 10)
        self.assertEqual(plan.capas_faltantes, [pa.CAPA_CONTENEDOR])
        self.assertFalse(plan.es_viable)

    def test_total_que_cabe_sin_tarea_imprescindible_no_es_viable(self):
        plan = pa.planificar(tareas_sin("Respuesta con fuente y cantidad"), 10)
        self.assertLessEqual(plan.horas_usadas, 10)
        self.assertEqual(plan.capas_faltantes, [])
        self.assertEqual(plan.rf_imprescindibles_sin_cubrir, ["RF-04"])
        self.assertFalse(plan.es_viable)

    def test_main_devuelve_cero_con_plan_viable(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(pa.main(), 0)


if __name__ == "__main__":
    unittest.main()
