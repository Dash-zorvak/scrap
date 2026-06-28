"""Test del desglose completo de ramas en la Concentración Temática.

Verifica que calcular_concentracion ya no deja el resto agrupado, sino que
devuelve cada tema con su proporción (clave `ramas`).
"""

from dashboard.dash_pulso import calcular_concentracion


class TestRamas:
    def test_incluye_todas_las_ramas(self):
        r = calcular_concentracion({"A": 60, "B": 30, "C": 10})
        assert "ramas" in r
        assert len(r["ramas"]) == 3

    def test_ramas_ordenadas_desc_con_proporcion(self):
        r = calcular_concentracion({"A": 60, "B": 30, "C": 10})
        ramas = r["ramas"]
        assert ramas[0]["tema"] == "A" and ramas[0]["share"] == 60.0
        assert ramas[1]["tema"] == "B" and ramas[1]["share"] == 30.0
        assert ramas[2]["tema"] == "C" and ramas[2]["share"] == 10.0

    def test_shares_suman_cien(self):
        r = calcular_concentracion({"X": 1, "Y": 1, "Z": 1})
        assert abs(sum(x["share"] for x in r["ramas"]) - 100.0) < 0.5

    def test_conteos_se_conservan(self):
        r = calcular_concentracion({"A": 7, "B": 3})
        assert sum(x["n"] for x in r["ramas"]) == 10

    def test_vacio(self):
        assert calcular_concentracion({}) is None
        assert calcular_concentracion(None) is None
