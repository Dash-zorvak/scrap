"""Tests for _clasificar_groq_lote: confidence parsing, mismatch, and fallback."""
import json
import pytest
from dashboard.sentimiento_engine import _clasificar_groq_lote, _SCORE_RESPALDO_GROQ


def _mock_chat_texto(textos, parsed_response):
    """Build a patcher-friendly lambda that returns a given JSON structure."""
    raw = json.dumps(parsed_response)
    return lambda prompt, json=True, temperature=0, max_tokens=4096: (raw, "stop", None)


class TestGroqConfianzaValida:
    """Caso 1: Groq devuelve confianza válida para todos → se usa tal cual, sin warnings."""

    def test_confianza_valida_en_todos(self, monkeypatch, caplog):
        textos = ["me encanta", "es un desastre"]
        groq_response = {"resultados": [
            {"label": "POS", "confianza": 0.94},
            {"label": "NEG", "confianza": 0.87},
        ]}
        monkeypatch.setattr(
            "dashboard.sentimiento_engine.chat_texto",
            _mock_chat_texto(textos, groq_response),
        )
        caplog.set_level("WARNING")
        resultados = _clasificar_groq_lote(textos)
        assert resultados == [("POS", 0.94), ("NEG", 0.87)]
        assert len(caplog.records) == 0


class TestGroqConfianzaInvalida:
    """Caso 2: confianza faltante, no numérica, o fuera de [0,1] → cae a 0.7 y loguea warning."""

    @pytest.mark.parametrize("confianza", [None, "alta", True, False, -0.1, 1.5])
    def test_confianza_invalida_loguea_warning(self, monkeypatch, caplog, confianza):
        textos = ["texto de prueba"]
        groq_response = {"resultados": [
            {"label": "POS", "confianza": confianza},
        ]}
        monkeypatch.setattr(
            "dashboard.sentimiento_engine.chat_texto",
            _mock_chat_texto(textos, groq_response),
        )
        caplog.set_level("WARNING")
        resultados = _clasificar_groq_lote(textos)
        assert resultados == [("POS", _SCORE_RESPALDO_GROQ)]
        assert any("confianza' válida" in r.message for r in caplog.records)

    def test_confianza_mezcla_valida_e_invalida(self, monkeypatch, caplog):
        textos = ["bueno", "malo", "regular"]
        groq_response = {"resultados": [
            {"label": "POS", "confianza": 0.92},
            {"label": "NEG", "confianza": None},
            {"label": "NEU", "confianza": 0.65},
        ]}
        monkeypatch.setattr(
            "dashboard.sentimiento_engine.chat_texto",
            _mock_chat_texto(textos, groq_response),
        )
        caplog.set_level("WARNING")
        resultados = _clasificar_groq_lote(textos)
        assert resultados == [("POS", 0.92), ("NEG", _SCORE_RESPALDO_GROQ), ("NEU", 0.65)]
        assert any("confianza' válida" in r.message for r in caplog.records)


class TestGroqMismatch:
    """Caso 3: menos resultados que textos → faltantes NEU/0.7, warning de mismatch,
    y los resultados existentes usan su propia confianza si es válida."""

    def test_faltante_se_completa_y_logea_mismatch(self, monkeypatch, caplog):
        textos = ["positivo total", "negativo total", "neutro"]
        groq_response = {"resultados": [
            {"label": "POS", "confianza": 0.95},
        ]}
        monkeypatch.setattr(
            "dashboard.sentimiento_engine.chat_texto",
            _mock_chat_texto(textos, groq_response),
        )
        caplog.set_level("WARNING")
        resultados = _clasificar_groq_lote(textos)
        # El primero usa su confianza real; los otros 2 son respaldo
        assert resultados == [
            ("POS", 0.95),
            ("NEU", _SCORE_RESPALDO_GROQ),
            ("NEU", _SCORE_RESPALDO_GROQ),
        ]
        assert any("devolvió 1 resultados" in r.message for r in caplog.records)

    def test_mismatch_con_confianza_valida_en_existentes(self, monkeypatch, caplog):
        textos = ["a", "b", "c", "d"]
        groq_response = {"resultados": [
            {"label": "POS", "confianza": 0.90},
            {"label": "NEG", "confianza": 0.80},
        ]}
        monkeypatch.setattr(
            "dashboard.sentimiento_engine.chat_texto",
            _mock_chat_texto(textos, groq_response),
        )
        caplog.set_level("WARNING")
        resultados = _clasificar_groq_lote(textos)
        assert resultados == [
            ("POS", 0.90),
            ("NEG", 0.80),
            ("NEU", _SCORE_RESPALDO_GROQ),
            ("NEU", _SCORE_RESPALDO_GROQ),
        ]
        assert any("devolvió 2 resultados" in r.message for r in caplog.records)


class TestGroqSinWarnings:
    """Caso 4: todo correcto (conteo + confianza válida) → sin warnings."""

    def test_limpio_sin_warnings(self, monkeypatch, caplog):
        textos = ["feliz", "enojado", "quizas"]
        groq_response = {"resultados": [
            {"label": "POS", "confianza": 0.96},
            {"label": "NEG", "confianza": 0.91},
            {"label": "NEU", "confianza": 0.72},
        ]}
        monkeypatch.setattr(
            "dashboard.sentimiento_engine.chat_texto",
            _mock_chat_texto(textos, groq_response),
        )
        caplog.set_level("WARNING")
        resultados = _clasificar_groq_lote(textos)
        assert resultados == [("POS", 0.96), ("NEG", 0.91), ("NEU", 0.72)]
        assert len(caplog.records) == 0
