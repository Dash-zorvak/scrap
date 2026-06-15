import pytest
from dashboard.muestra import evaluar_muestra
from dashboard.config import MIN_COMENTARIOS_MUESTRA


class TestEvaluarMuestra:
    def test_cero(self):
        r = evaluar_muestra(0)
        assert r["n"] == 0
        assert r["suficiente"] is False
        assert r["emoji"] == "⚠️"

    def test_insuficiente(self):
        r = evaluar_muestra(14)
        assert r["n"] == 14
        assert r["suficiente"] is False
        assert r["emoji"] == "⚠️"

    def test_justo_en_limite(self):
        r = evaluar_muestra(15)
        assert r["n"] == 15
        assert r["suficiente"] is True
        assert r["emoji"] == "✅"

    def test_suficiente(self):
        r = evaluar_muestra(30)
        assert r["n"] == 30
        assert r["suficiente"] is True
        assert r["emoji"] == "✅"

    def test_none_no_rompe(self):
        r = evaluar_muestra(None)
        assert r["n"] == 0
        assert r["suficiente"] is False
        assert r["emoji"] == "⚠️"

    def test_etiqueta_menciona_minimo(self):
        r = evaluar_muestra(5)
        assert str(MIN_COMENTARIOS_MUESTRA) in r["etiqueta"]
        assert "muestra insuficiente" in r["etiqueta"]
