"""Tests: st.toast se llama en puntos de espera de topic_llm."""
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import dashboard.topic_llm as tl

TEXTO = ["Foco fundido en la colonia San Miguelito"]
JSON_VALIDO = json.dumps({
    "resultados": [{"categoria": "alumbrado", "tono": "literal", "postura": "neutral", "confianza": 0.9}],
})


class TestToastEnEsperaPresupuesto:

    def test_toast_llamado_en_pacing(self, monkeypatch):
        toast_calls = []
        monkeypatch.setattr(tl.st, "toast", lambda msg, **kw: toast_calls.append(msg))
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr(tl, "_purgar_historial", lambda ahora: None)
        monkeypatch.setattr(tl, "_historial_tokens", [(0, 99999)])  # fuerza espera
        monkeypatch.setattr(tl, "TPM_BUDGET", 100)
        monkeypatch.setattr(tl, "_registrar_tokens", lambda x: None)

        # Necesito llamar a _clasificar_bloque_llm para que se ejecute _esperar_presupuesto
        monkeypatch.setattr("dashboard.llm_groq.chat_texto",
                            lambda *a, **kw: (JSON_VALIDO, "stop", None))
        monkeypatch.setattr("dashboard.llm_groq.groq_disponible", lambda: True)

        tl._clasificar_bloque_llm(TEXTO)

        assert len(toast_calls) >= 1
        assert any("Esperando presupuesto" in m for m in toast_calls)


class TestToastEnRateLimit:

    def test_toast_llamado_en_rate_limit(self, monkeypatch):
        toast_calls = []
        monkeypatch.setattr(tl.st, "toast", lambda msg, **kw: toast_calls.append(msg))
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr(tl, "_esperar_presupuesto", lambda x: None)
        monkeypatch.setattr(tl, "_registrar_tokens", lambda x: None)
        monkeypatch.setattr(tl, "MAX_REINTENTOS_429", 2)

        intentos = [0]

        def mock_chat_texto(*a, **kw):
            intentos[0] += 1
            if intentos[0] == 1:
                raise Exception("429 Too Many Requests")
            return (JSON_VALIDO, "stop", None)

        monkeypatch.setattr("dashboard.llm_groq.chat_texto", mock_chat_texto)

        tl._clasificar_bloque_llm(TEXTO)

        assert len(toast_calls) >= 1
        assert any("Límite de IA" in m for m in toast_calls)


class TestToastEnRespuestaVacia:

    def test_toast_llamado_en_respuesta_vacia(self, monkeypatch):
        toast_calls = []
        monkeypatch.setattr(tl.st, "toast", lambda msg, **kw: toast_calls.append(msg))
        monkeypatch.setattr("time.sleep", lambda s: None)
        monkeypatch.setattr(tl, "_esperar_presupuesto", lambda x: None)
        monkeypatch.setattr(tl, "_registrar_tokens", lambda x: None)
        monkeypatch.setattr(tl, "MAX_REINTENTOS_429", 2)

        intentos = [0]

        def mock_chat_texto(*a, **kw):
            intentos[0] += 1
            if intentos[0] == 1:
                return ("", "stop", None)
            return (JSON_VALIDO, "stop", None)

        monkeypatch.setattr("dashboard.llm_groq.chat_texto", mock_chat_texto)

        tl._clasificar_bloque_llm(TEXTO)

        assert len(toast_calls) >= 1
        assert any("Respuesta vacía" in m for m in toast_calls)
