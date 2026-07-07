"""Tests para el cliente LLM (dashboard/llm_groq.py).

Verifican que chat_texto agregue extra_body para desactivar el modo de
razonamiento en modelos DeepSeek (NVIDIA NIM). No se toca la red: el cliente
OpenAI se mockea.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import logging
import pytest
from unittest.mock import MagicMock
import dashboard.llm_groq as lg


def _mock_openai_client():
    """Crea un mock del cliente OpenAI con chat.completions.create."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "respuesta de prueba"
    mock_choice.finish_reason = "stop"
    mock_choice.message.reasoning_content = None
    mock_resp.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_client


def test_chat_texto_deepseek_incluye_extra_body_thinking_false(monkeypatch):
    """Test A: modelo DeepSeek → extra_body con thinking=False en la llamada real."""
    mock_client = _mock_openai_client()
    monkeypatch.setattr(lg, "_get_text_client", lambda: mock_client)

    # Pasar el modelo DeepSeek explícitamente en vez de depender de TEXT_MODEL,
    # que puede quedar fijado como default en la firma de chat_texto al importar el módulo.
    content, finish_reason, reasoning = lg.chat_texto(
        "prompt de prueba", model="deepseek-ai/deepseek-v4-flash"
    )

    # Verificar que la llamada al cliente incluyó extra_body
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "extra_body" in call_kwargs, "extra_body debe estar presente para DeepSeek"
    assert call_kwargs["extra_body"] == {"chat_template_kwargs": {"thinking": False}}
    # Verificar respuesta
    assert content == "respuesta de prueba"
    assert finish_reason == "stop"
    assert reasoning is None


def test_chat_texto_no_deepseek_no_agrega_extra_body(monkeypatch):
    """Test B: modelo no-DeepSeek (GLM verificador) → NO extra_body en la llamada."""
    mock_client = _mock_openai_client()
    monkeypatch.setattr(lg, "_get_text_client", lambda: mock_client)
    # Forzar modelo no-DeepSeek (el verificador)
    monkeypatch.setattr(lg, "VERIFIER_MODEL", "z-ai/glm-5.1")

    # Llamar a chat_texto pasando modelo GLM explícitamente
    content, finish_reason, reasoning = lg.chat_texto(
        "prompt de prueba", model="z-ai/glm-5.1"
    )

    # Verificar que NO hay extra_body
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "extra_body" not in call_kwargs, "NO debe haber extra_body para modelo no-DeepSeek"
    # Verificar respuesta
    assert content == "respuesta de prueba"
    assert finish_reason == "stop"
    assert reasoning is None


def test_es_modelo_deepseek_variantes():
    """Helper: _es_modelo_deepseek detecta variantes del nombre."""
    assert lg._es_modelo_deepseek("deepseek-ai/deepseek-v4-flash") is True
    assert lg._es_modelo_deepseek("deepseek-ai/deepseek-v4-pro") is True
    assert lg._es_modelo_deepseek("DeepSeek-V4") is True
    assert lg._es_modelo_deepseek("z-ai/glm-5.1") is False
    assert lg._es_modelo_deepseek("qwen/qwen3.5-397b-a17b") is False
    assert lg._es_modelo_deepseek("") is False
    assert lg._es_modelo_deepseek(None) is False


class TestRetryBackoffLogging:

    def test_logs_backoff_en_rate_limit(self, caplog, monkeypatch):
        caplog.set_level(logging.INFO, logger="dashboard.llm_groq")
        monkeypatch.setattr(lg, "_MAX_REINTENTOS", 2)

        llamadas = [0]

        def func_que_falla():
            llamadas[0] += 1
            if llamadas[0] == 1:
                raise Exception("429 Too Many Requests")
            return "ok"

        monkeypatch.setattr("time.sleep", lambda s: None)
        resultado = lg._retry_with_backoff(func_que_falla)

        assert resultado == "ok"
        records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(records) >= 1
        assert any("Backoff" in r.message for r in records)

    def test_no_log_si_no_hay_reintento(self, caplog, monkeypatch):
        caplog.set_level(logging.INFO, logger="dashboard.llm_groq")
        monkeypatch.setattr(lg, "_MAX_REINTENTOS", 2)

        def func_ok():
            return "ok"

        resultado = lg._retry_with_backoff(func_ok)
        assert resultado == "ok"
        records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(records) == 0