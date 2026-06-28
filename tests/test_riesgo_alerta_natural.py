"""Test del Nivel de Alerta en lenguaje natural.

Verifica que la alerta nombra los temas a los que hay que responder, explica
qué significa (detalle) y por qué está en ese nivel (factores), sin romper la
retrocompatibilidad de color/riesgo.
"""

from dashboard.dash_riesgo import calcular_nivel_alerta


class TestAlertaNatural:
    def test_amarillo_menciona_tema(self):
        r = calcular_nivel_alerta(
            pct_negativo=30, indice_enojo=0.1, balance_confrontacion=0.3,
            n_fricciones=1, temas_friccion=[{"tema": "Baches"}],
        )
        assert r["color"] == "amarillo"
        assert "Baches" in r["foco"]
        assert "Baches" in r["accion"]
        assert "Baches" in r["detalle"]

    def test_rojo_lista_varios_temas(self):
        r = calcular_nivel_alerta(
            pct_negativo=60, indice_enojo=0.5, balance_confrontacion=0.8,
            n_fricciones=3,
            temas_friccion=[{"tema": "Agua"}, {"tema": "Baches"}, {"tema": "Basura"}],
        )
        assert r["color"] == "rojo"
        assert "Agua" in r["accion"] and "Basura" in r["accion"]

    def test_verde_sin_temas_no_falla(self):
        r = calcular_nivel_alerta(
            pct_negativo=5, indice_enojo=0.02, balance_confrontacion=0.1,
        )
        assert r["color"] == "verde"
        assert r["foco"] == ""
        assert r["accion"] and r["detalle"]

    def test_ignora_tema_general(self):
        r = calcular_nivel_alerta(
            pct_negativo=30, indice_enojo=0.1, balance_confrontacion=0.3,
            n_fricciones=1, temas_friccion=[{"tema": "general"}],
        )
        assert r["foco"] == ""

    def test_factores_presentes(self):
        r = calcular_nivel_alerta(
            pct_negativo=30, indice_enojo=0.1, balance_confrontacion=0.3,
            n_fricciones=1, temas_friccion=[{"tema": "Baches"}],
        )
        assert any("negativos" in f for f in r["factores"])
        assert isinstance(r["factores"], list) and len(r["factores"]) >= 2
