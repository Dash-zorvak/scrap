"""Tests for Fase 5: sentimiento_engine cascade (BERT → Gemini → reglas)."""
import pytest
from dashboard.sentimiento_engine import clasificar_lote, analizar_sentimiento_rapido


class TestAnalizarSentimientoRapido:
    def test_positivo(self):
        label, score = analizar_sentimiento_rapido("excelente trabajo gracias")
        assert label == "POS"
        assert 0 < score <= 1

    def test_negativo(self):
        label, score = analizar_sentimiento_rapido("pesimo corrupto incompetente")
        assert label == "NEG"
        assert 0 < score <= 1

    def test_neutral(self):
        label, score = analizar_sentimiento_rapido("la reunion fue el martes")
        assert label == "NEU"
        assert score == 0.0

    def test_vacio(self):
        label, score = analizar_sentimiento_rapido("")
        assert label == "NEU"
        assert score == 0.0

    def test_none(self):
        label, score = analizar_sentimiento_rapido(None)
        assert label == "NEU"
        assert score == 0.0


class TestClasificarLoteReglas:
    """Tests that use reglas fallback by default (no BERT/Gemini in CI)."""

    def test_empty_list(self):
        resultados, motor = clasificar_lote([])
        assert resultados == []
        assert motor == "reglas"

    def test_all_empty_texts(self):
        resultados, motor = clasificar_lote(["", None, "   "])
        assert all(r == ("NEU", 0.0) for r in resultados)
        assert motor == "reglas"

    def test_mixed_empty_and_real(self, monkeypatch):
        def mock_cargar_bert():
            raise ImportError("No BERT")
        monkeypatch.setattr("dashboard.sentimiento_engine._cargar_bert", mock_cargar_bert)
        monkeypatch.setattr("dashboard.sentimiento_engine._configurar_gemini", lambda: False)
        textos = ["", "excelente trabajo", None, "pesimo corrupto"]
        resultados, motor = clasificar_lote(textos)
        assert motor == "reglas"
        assert resultados[0] == ("NEU", 0.0)
        assert resultados[2] == ("NEU", 0.0)
        assert resultados[1][0] == "POS"
        assert resultados[3][0] == "NEG"


class TestClasificarLoteBert:
    """Test BERT path with mocked analyzer."""

    def test_bert_path(self, monkeypatch):
        class MockOutput:
            def __init__(self, label, proba):
                self.output = label
                self.probas = {label: proba}
        class MockAnalyzer:
            def predict(self, textos):
                return [MockOutput("POS", 0.95), MockOutput("NEG", 0.88)]
        def mock_cargar_bert():
            return MockAnalyzer()
        monkeypatch.setattr("dashboard.sentimiento_engine._cargar_bert", mock_cargar_bert)
        resultados, motor = clasificar_lote(["muy bueno", "horrible"])
        assert motor == "bert"
        assert resultados[0] == ("POS", 0.95)
        assert resultados[1] == ("NEG", 0.88)

    def test_bert_fallsback_to_gemini(self, monkeypatch):
        def mock_cargar_bert():
            raise RuntimeError("BERT load failed")
        monkeypatch.setattr("dashboard.sentimiento_engine._cargar_bert", mock_cargar_bert)
        monkeypatch.setattr("dashboard.sentimiento_engine._configurar_gemini", lambda: True)
        monkeypatch.setattr(
            "dashboard.sentimiento_engine._clasificar_gemini_lote",
            lambda textos: [("POS", 0.7), ("NEU", 0.7)]
        )
        resultados, motor = clasificar_lote(["buen trabajo", "ayer llovio"])
        assert motor == "gemini"
        assert resultados[0] == ("POS", 0.7)
        assert resultados[1] == ("NEU", 0.7)

    def test_bert_and_gemini_fall_to_reglas(self, monkeypatch):
        def mock_cargar_bert():
            raise RuntimeError("BERT failed")
        monkeypatch.setattr("dashboard.sentimiento_engine._cargar_bert", mock_cargar_bert)
        monkeypatch.setattr("dashboard.sentimiento_engine._configurar_gemini", lambda: False)
        resultados, motor = clasificar_lote(["excelente genial", "pesimo horrible"])
        assert motor == "reglas"
        assert resultados[0][0] == "POS"
        assert resultados[1][0] == "NEG"
