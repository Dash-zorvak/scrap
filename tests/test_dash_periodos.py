"""Tests: DASHBOARD_FECHA_CORTE_MINIMA configurable y logger en dash_periodos."""
import logging
from datetime import datetime

import dashboard.dash_periodos as dp


class TestFechaCorteMinima:

    def test_default_20200101(self):
        assert dp.DASHBOARD_FECHA_CORTE_MINIMA == datetime(2020, 1, 1, 0, 0, 0)

    def test_entorno_personalizado(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_FECHA_CORTE_MINIMA", "2021-06-15")
        import importlib
        importlib.reload(dp)
        assert dp.DASHBOARD_FECHA_CORTE_MINIMA == datetime(2021, 6, 15, 0, 0, 0)

    def test_invalido_cae_a_default_y_loggea_warning(self, monkeypatch, caplog):
        monkeypatch.setenv("DASHBOARD_FECHA_CORTE_MINIMA", "no-es-fecha")
        caplog.set_level(logging.WARNING, logger="dashboard.dash_periodos")
        import importlib
        importlib.reload(dp)
        assert dp.DASHBOARD_FECHA_CORTE_MINIMA == datetime(2020, 1, 1, 0, 0, 0)
        assert any("inválida" in r.message for r in caplog.records)


class TestRangoPeriodoUsaCorte:

    def test_todo_el_periodo_respeta_corte(self):
        fin = datetime(2026, 7, 7, 23, 59, 59)
        inicio, fin_r = dp.rango_periodo("Todo el periodo", fecha_ref=datetime(2026, 7, 7))
        assert inicio == dp.DASHBOARD_FECHA_CORTE_MINIMA
        assert fin_r == fin

    def test_default_respeta_corte(self):
        inicio, fin = dp.rango_periodo("inexistente", fecha_ref=datetime(2026, 7, 7))
        assert inicio == dp.DASHBOARD_FECHA_CORTE_MINIMA
