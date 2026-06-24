"""Tests del Bloque II (polarizacion: consenso vs confrontacion)."""

from dashboard.dash_audiencia import calcular_polarizacion


class TestPolarizacion:
    def test_confrontacion_total(self):
        r = calcular_polarizacion([0.5, 0.5, -0.5, -0.5])
        assert r is not None
        assert r["nivel"] == "confrontacion"
        assert r["balance"] == 1.0
        assert r["intensidad"] == 1.0
        assert r["indice"] == 100.0
        assert r["pct_favor"] == 50.0
        assert r["pct_contra"] == 50.0

    def test_consenso_favorable(self):
        r = calcular_polarizacion([0.5] * 9 + [-0.5])
        assert r["nivel"] == "consenso"
        assert r["lado"] == "favor"
        assert r["balance"] == 0.2

    def test_dividida(self):
        r = calcular_polarizacion([0.5, 0.5, 0.5, -0.5, -0.5])
        assert r["nivel"] == "dividida"
        assert r["lado"] == "favor"

    def test_mayoria_neutral(self):
        r = calcular_polarizacion([0.0, 0.0, 0.05, -0.05])
        assert r["nivel"] == "consenso"
        assert r["lado"] == "neutral"
        assert r["indice"] == 0.0

    def test_vacio(self):
        assert calcular_polarizacion([]) is None
        assert calcular_polarizacion(None) is None
