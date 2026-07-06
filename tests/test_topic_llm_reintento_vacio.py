"""Bug D21: _clasificar_bloque_llm reintenta respuesta vacía antes de caer a fallback.

Casos:
1. Vacío → vacío → válido: reintenta con ESPERA_VACIO_DEFAULT, no con ESPERA_429_DEFAULT.
2. Todas las respuestas vacías: lanza ValueError, no cae silenciosamente a fallback.
3. Vacío → 429: usa ESPERA_VACIO_DEFAULT para el vacío, ESPERA_429_DEFAULT para el rate limit.
4. Válido a la primera: sin sleep, devuelve el resultado parseado.
"""

import sys
import os
import time
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import dashboard.topic_llm as tl

ESPERA_VACIO = tl.ESPERA_VACIO_DEFAULT
ESPERA_429 = tl.ESPERA_429_DEFAULT

TEXTO = ["Foco fundido en la colonia San Miguelito"]
JSON_VALIDO = json.dumps({
    "resultados": [{"categoria": "alumbrado", "tono": "literal", "postura": "neutral", "confianza": 0.9}],
})


def _resultado_parseado():
    return tl._parsear_respuesta(JSON_VALIDO, TEXTO)


class TestClasificarBloqueLLMReintentoVacio:

    def test_vacio_luego_valido_reintenta_con_espera_corta(self, monkeypatch):
        chat_returns = [
            ("", "stop", None),
            (JSON_VALIDO, "stop", None),
        ]
        call_idx = [0]

        def mock_chat_texto(prompt, **kw):
            result = chat_returns[call_idx[0]]
            call_idx[0] += 1
            return result

        monkeypatch.setattr("dashboard.llm_groq.chat_texto", mock_chat_texto)
        monkeypatch.setattr(tl, "_esperar_presupuesto", lambda x: None)
        monkeypatch.setattr(tl, "_registrar_tokens", lambda x: None)

        sleep_calls = []
        monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

        result = tl._clasificar_bloque_llm(TEXTO)

        assert call_idx[0] == 2
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == ESPERA_VACIO
        assert result == _resultado_parseado()

    def test_todas_vacias_lanza_exception(self, monkeypatch):
        n = tl.MAX_REINTENTOS_429 + 1
        chat_returns = [("", "stop", None)] * n
        call_idx = [0]

        def mock_chat_texto(prompt, **kw):
            result = chat_returns[call_idx[0]]
            call_idx[0] += 1
            return result

        monkeypatch.setattr("dashboard.llm_groq.chat_texto", mock_chat_texto)
        monkeypatch.setattr(tl, "_esperar_presupuesto", lambda x: None)
        monkeypatch.setattr(tl, "_registrar_tokens", lambda x: None)
        monkeypatch.setattr("time.sleep", lambda s: None)

        with pytest.raises(ValueError) as excinfo:
            tl._clasificar_bloque_llm(TEXTO)
        assert "vacío" in str(excinfo.value).lower()
        assert call_idx[0] == n

    def test_vacio_luego_429_respeta_ambas_esperas(self, monkeypatch):
        chat_returns = [
            ("", "stop", None),
            Exception("429 Too Many Requests"),
            (JSON_VALIDO, "stop", None),
        ]
        call_idx = [0]

        def mock_chat_texto(prompt, **kw):
            result = chat_returns[call_idx[0]]
            call_idx[0] += 1
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr("dashboard.llm_groq.chat_texto", mock_chat_texto)
        monkeypatch.setattr(tl, "_esperar_presupuesto", lambda x: None)
        monkeypatch.setattr(tl, "_registrar_tokens", lambda x: None)

        sleep_calls = []
        monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

        result = tl._clasificar_bloque_llm(TEXTO)

        assert call_idx[0] == 3
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == ESPERA_VACIO
        assert sleep_calls[1] == ESPERA_429
        assert result == _resultado_parseado()

    def test_valido_primer_intento_sin_sleep(self, monkeypatch):
        def mock_chat_texto(prompt, **kw):
            return (JSON_VALIDO, "stop", None)

        monkeypatch.setattr("dashboard.llm_groq.chat_texto", mock_chat_texto)
        monkeypatch.setattr(tl, "_esperar_presupuesto", lambda x: None)
        monkeypatch.setattr(tl, "_registrar_tokens", lambda x: None)

        sleep_calls = []
        monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

        result = tl._clasificar_bloque_llm(TEXTO)

        assert len(sleep_calls) == 0
        assert result == _resultado_parseado()
