"""Tests para analytics/narrator_claude.py."""
import json
import pytest
from unittest.mock import patch, MagicMock


def test_redactar_narrativa_sin_api_key():
    """Sin ANTHROPIC_API_KEY lanza ValueError."""
    from analytics.narrator_claude import redactar_narrativa
    with patch.dict("os.environ", {}, clear=True):
        # Remove the key if it exists
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            redactar_narrativa("system", {"dato": 1})


def test_redactar_narrativa_envia_contexto_correcto():
    """El prompt de usuario contiene exactamente los numeros del contexto."""
    from analytics.narrator_claude import redactar_narrativa

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Narrativa de prueba.")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    contexto = {
        "n_total_comentarios": 430,
        "pct_favorable": 37.0,
        "pct_critico": 29.0,
        "tono_dominante": "mixto",
    }

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"}):
        with patch("analytics.narrator_claude.Anthropic", return_value=mock_client):
            resultado = redactar_narrativa(
                "Eres un redactor.",
                contexto,
                section_code="test",
            )

    assert resultado == "Narrativa de prueba."

    # Verificar que el prompt contiene los numeros exactos del contexto
    call_args = mock_client.messages.create.call_args
    user_msg = call_args[1]["messages"][0]["content"]
    assert "430" in user_msg
    assert "37.0" in user_msg
    assert "29.0" in user_msg
    assert "mixto" in user_msg


def test_redactar_narrativa_no_inventa_numeros():
    """Claude recibe los numeros del contexto; el system prompt le prohiebe inventar."""
    from analytics.narrator_claude import redactar_narrativa

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Resultado.")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    contexto = {"n_total_comentarios": 100, "pct_favorable": 50.0}

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("analytics.narrator_claude.Anthropic", return_value=mock_client):
            redactar_narrativa("System.", contexto, section_code="test")

    call_args = mock_client.messages.create.call_args
    user_msg = call_args[1]["messages"][0]["content"]
    assert "No inventes" in user_msg or "No calcules" in user_msg


def test_redactar_narrativa_usa_modelo_configurado():
    """Usa CLAUDE_MODEL y CLAUDE_TEMPERATURE de entorno."""
    from analytics.narrator_claude import redactar_narrativa

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Ok")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch.dict("os.environ", {
        "ANTHROPIC_API_KEY": "test-key",
        "CLAUDE_MODEL": "claude-opus-4",
        "CLAUDE_TEMPERATURE": "0.1",
    }):
        with patch("analytics.narrator_claude.Anthropic", return_value=mock_client):
            redactar_narrativa("System.", {"x": 1}, section_code="test")

    call_args = mock_client.messages.create.call_args
    assert call_args[1]["model"] == "claude-opus-4"
    assert call_args[1]["temperature"] == 0.1


def test_redactar_narrativa_reintenta_en_rate_limit():
    """Reintenta ante error 429 y exito en segundo intento."""
    from analytics.narrator_claude import redactar_narrativa
    import time

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Exito")]

    mock_client = MagicMock()
    # Primer llamado falla con rate limit, segundo exito
    rate_error = Exception("429 Too Many Requests")
    mock_client.messages.create.side_effect = [rate_error, mock_response]

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("analytics.narrator_claude.Anthropic", return_value=mock_client):
            with patch("analytics.narrator_claude.time.sleep"):
                resultado = redactar_narrativa("System.", {"x": 1}, section_code="test")

    assert resultado == "Exito"
    assert mock_client.messages.create.call_count == 2


def test_redactar_narrativa_propaga_error_no_recuperable():
    """Errores que no son rate-limit/timeout se propagan inmediatamente."""
    from analytics.narrator_claude import redactar_narrativa

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Invalid API key")

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("analytics.narrator_claude.Anthropic", return_value=mock_client):
            with pytest.raises(Exception, match="Invalid API key"):
                redactar_narrativa("System.", {"x": 1}, section_code="test")

    assert mock_client.messages.create.call_count == 1
