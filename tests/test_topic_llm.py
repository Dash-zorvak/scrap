"""Tests para topic_llm.py: diagnóstico de respuesta vacía del LLM."""
import logging
import pytest
from unittest.mock import patch, MagicMock
import json

import dashboard.topic_llm as topic_llm
from dashboard import llm_groq


def test_clasificar_bloque_llm_logs_empty_content_with_finish_reason_length(caplog):
    """Verifica que se loguee warning cuando chat_texto devuelve contenido vacío
    con finish_reason='length'."""
    
    with caplog.at_level(logging.WARNING, logger="topic_llm"):
        # Mock chat_texto to return empty content with finish_reason="length"
        def mock_chat_texto(prompt, **kwargs):
            return "", "length", None
        
        with patch("dashboard.llm_groq.chat_texto", mock_chat_texto):
            with patch("dashboard.llm_groq.groq_disponible", return_value=True):
                textos = ["comentario de prueba"]
                # The function will log the warning and then raise JSONDecodeError
                # when trying to parse the empty response
                with pytest.raises(json.JSONDecodeError):
                    topic_llm._clasificar_bloque_llm(textos)
    
    # Verify the warning was logged with finish_reason and reasoning_content info
    assert len(caplog.records) >= 1
    warning_msg = caplog.records[0].message
    assert "LLM devolvió contenido vacío" in warning_msg
    assert "finish_reason=length" in warning_msg
    assert "reasoning_content=ausente" in warning_msg


def test_clasificar_bloque_llm_logs_empty_content_with_finish_reason_stop(caplog):
    """Verifica que se loguee warning cuando chat_texto devuelve contenido vacío
    con finish_reason='stop'."""
    
    with caplog.at_level(logging.WARNING, logger="topic_llm"):
        # Mock chat_texto to return empty content with finish_reason="stop"
        def mock_chat_texto(prompt, **kwargs):
            return "", "stop", "algun razonamiento"
        
        with patch("dashboard.llm_groq.chat_texto", mock_chat_texto):
            with patch("dashboard.llm_groq.groq_disponible", return_value=True):
                textos = ["comentario de prueba"]
                # The function will log the warning and then raise JSONDecodeError
                with pytest.raises(json.JSONDecodeError):
                    topic_llm._clasificar_bloque_llm(textos)
    
    # Verify the warning was logged with finish_reason and reasoning_content info
    assert len(caplog.records) >= 1
    warning_msg = caplog.records[0].message
    assert "LLM devolvió contenido vacío" in warning_msg
    assert "finish_reason=stop" in warning_msg
    assert "reasoning_content=presente" in warning_msg


def test_clasificar_bloque_llm_normal_response_no_warning(caplog):
    """Verifica que NO se loguee warning cuando la respuesta es normal."""
    
    with caplog.at_level(logging.WARNING, logger="topic_llm"):
        def mock_chat_texto(prompt, **kwargs):
            return '{"resultados": [{"categoria": "seguridad", "tono": "literal", "postura": "neutral", "confianza": 0.8}]}', "stop", None
        
        with patch("dashboard.llm_groq.chat_texto", mock_chat_texto):
            with patch("dashboard.llm_groq.groq_disponible", return_value=True):
                textos = ["comentario de prueba"]
                resultado = topic_llm._clasificar_bloque_llm(textos)
    
    # No warning should be logged for normal responses
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 0
    
    # Result should come from LLM
    assert len(resultado) == 1
    assert resultado[0]["motor"] == "llm"
    assert resultado[0]["categoria"] == "seguridad"