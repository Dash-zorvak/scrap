"""Regresión D9: logging y fallback en topic_llm.clasificar_temas_lote.

Verifica que:
- Excepción en groq_disponible() → logger.warning con error + len(textos) → fallback a _fallback_keyword
- groq_disponible() == False → logger.warning "sin API key" + len(textos) → fallback
- logger.warning existente en loop por bloques sigue funcionando (no duplicado ni removido)
"""

import sys
import os
import logging
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import dashboard.topic_llm as tl


class TestTopicLLMFallbackLogging:
    """Tests de regresión D9: logging + fallback en clasificar_temas_lote."""

    def test_groq_disponible_lanza_excepcion_warning_y_fallback_keyword(self, monkeypatch, caplog):
        """Test A: groq_disponible() lanza excepción → warning con error y len → _fallback_keyword."""
        # Mock groq_disponible para que lance excepción
        def raise_exception():
            raise Exception("conexión fallida")

        monkeypatch.setattr("dashboard.llm_groq.groq_disponible", raise_exception)

        # Mock st.warning para que no falle sin Streamlit
        mock_st_warning = MagicMock()
        monkeypatch.setattr(tl.st, "warning", mock_st_warning)

        textos = ["comentario 1", "comentario 2", "comentario 3"]

        with caplog.at_level(logging.WARNING, logger="topic_llm"):
            result = tl.clasificar_temas_lote(textos)

        # Verificar warning logueado con error y len(textos)
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1
        msg = warning_records[0].message
        assert "conexión fallida" in msg or "Exception" in msg
        assert "3" in msg  # len(textos)

        # Verificar st.warning llamado
        mock_st_warning.assert_called_once()

        # Verificar fallback a _fallback_keyword (motor = "reglas")
        assert len(result) == 3
        for r in result:
            assert r["motor"] == "reglas"
            assert r["postura"] == "neutral"
            assert r["tono"] == "literal"
            assert r["confianza"] == 0.3

    def test_groq_disponible_false_warning_sin_api_key_y_fallback_keyword(self, monkeypatch, caplog):
        """Test B: groq_disponible() == False → warning 'sin API key' + len → _fallback_keyword."""
        monkeypatch.setattr("dashboard.llm_groq.groq_disponible", lambda: False)

        mock_st_warning = MagicMock()
        monkeypatch.setattr(tl.st, "warning", mock_st_warning)

        textos = ["comentario A", "comentario B"]

        with caplog.at_level(logging.WARNING, logger="topic_llm"):
            result = tl.clasificar_temas_lote(textos)

        # Verificar warning con mensaje de "sin API key" (o el texto real del código)
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1
        msg = warning_records[0].message
        # El código usa: "IA no disponible para clasificar %d comentarios (sin API key configurada)"
        assert "sin API key" in msg.lower() or "api key" in msg.lower()
        assert "2" in msg  # len(textos)

        # st.warning llamado
        mock_st_warning.assert_called_once()

        # Fallback a _fallback_keyword
        assert len(result) == 2
        for r in result:
            assert r["motor"] == "reglas"
            assert r["postura"] == "neutral"
            assert r["tono"] == "literal"
            assert r["confianza"] == 0.3

    def test_warning_bloque_individual_sigue_funcionando_no_duplicado(self, monkeypatch, caplog):
        """Test C (no-regresión): warning en loop por bloques sigue funcionando igual.

        Simula que groq_disponible() = True pero _clasificar_bloque_llm falla en un bloque.
        Verifica que se loguea el warning del bloque (línea ~385-388) y se hace fallback.
        Con 4 items y lote=2, hay 2 bloques → 2 warnings (uno por bloque que falla).
        """
        # groq_disponible = True
        monkeypatch.setattr("dashboard.llm_groq.groq_disponible", lambda: True)
        # No hay verificador (CASCADA_ACTIVA = False o VERIFIER_MODEL = None)
        monkeypatch.setattr(tl, "CASCADA_ACTIVA", False)
        monkeypatch.setattr(tl, "_verifier_model", lambda: None)

        mock_st_warning = MagicMock()
        monkeypatch.setattr(tl.st, "warning", mock_st_warning)

        # Hacer que _clasificar_bloque_llm falle en el primer bloque
        original_clasificar_bloque = tl._clasificar_bloque_llm

        def mock_clasificar_bloque_falla(textos, model=None, ejemplos=None):
            raise Exception("fallo en bloque LLM")

        monkeypatch.setattr(tl, "_clasificar_bloque_llm", mock_clasificar_bloque_falla)

        textos = ["c1", "c2", "c3", "c4"]  # 2 bloques de 2
        # Forzar lote pequeño para tener 2 bloques
        monkeypatch.setattr(tl, "LOTE_LLM", 2)

        with caplog.at_level(logging.WARNING, logger="topic_llm"):
            result = tl.clasificar_temas_lote(textos, lote=2)

        # Debe haber warning del bloque que falló (línea 385-388 en topic_llm.py)
        # Con 2 bloques que fallan, esperamos 2 warnings
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        bloque_warnings = [r for r in warning_records if "Clasificacion IA fallo en bloque" in r.message]
        assert len(bloque_warnings) == 2, f"Esperaba 2 warnings de bloque (uno por cada bloque), got: {[r.message for r in warning_records]}"

        # Verificar que ambos warnings tienen el formato correcto
        for msg in [r.message for r in bloque_warnings]:
            assert "fallo en bloque LLM" in msg or "Fallo en bloque" in msg
            assert "2" in msg  # len(bloque)

        # Resultado: fallback para ambos bloques (4 items total)
        assert len(result) == 4
        for r in result:
            assert r["motor"] == "reglas"

        # st.warning NO debe llamarse aquí (solo en los excepts de groq_disponible)
        mock_st_warning.assert_not_called()

    def test_clasificar_temas_lote_vacio_devuelve_lista_vacia_sin_logs(self, caplog):
        """Sanity: lista vacía → [] sin warnings ni fallbacks."""
        with caplog.at_level(logging.WARNING, logger="topic_llm"):
            result = tl.clasificar_temas_lote([])

        assert result == []
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) == 0