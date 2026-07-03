"""Tests de la cascada de generación narrativa del Bloque IV.

Verifican que generar_narrativa_ia (dashboard/dash_metrics.py) use la cascada
NIM: primario DeepSeek y, si falla, respaldo con el verificador GLM. No se toca
la red: chat_texto se inyecta como un fake mediante monkeypatch.
"""
import dashboard.dash_metrics as dm


def _limpiar_cache():
    # generar_narrativa_ia está envuelta por st.cache_data; limpiamos su caché
    # para que cada test ejecute el cuerpo real con sus propios fakes.
    try:
        dm.generar_narrativa_ia.clear()
    except Exception:
        pass


def test_usa_primario_cuando_responde(monkeypatch):
    llamadas = []

    def fake_chat(prompt, max_tokens=600, temperature=0.6, json=False, model=None):
        llamadas.append(model)
        return "narrativa primario", "stop", None

    monkeypatch.setattr(dm, "groq_disponible", lambda: True)
    monkeypatch.setattr(dm, "chat_texto", fake_chat)
    monkeypatch.setattr(dm, "VERIFIER_MODEL", "glm-test")
    _limpiar_cache()

    out = dm.generar_narrativa_ia("recomendacion", {"score": 0.111, "n": 1})
    assert out == "narrativa primario"
    # Solo se llamó al primario (model=None); no hizo falta el verificador.
    assert llamadas == [None]


def test_cae_al_verificador_glm_si_falla_primario(monkeypatch):
    llamadas = []

    def fake_chat(prompt, max_tokens=600, temperature=0.6, json=False, model=None):
        llamadas.append(model)
        if model is None:
            raise RuntimeError("primario caido")
        return "narrativa verificador", "stop", None

    monkeypatch.setattr(dm, "groq_disponible", lambda: True)
    monkeypatch.setattr(dm, "chat_texto", fake_chat)
    monkeypatch.setattr(dm, "VERIFIER_MODEL", "glm-test")
    _limpiar_cache()

    out = dm.generar_narrativa_ia("eco_historico", {"score": 0.222, "n": 2})
    assert out == "narrativa verificador"
    # Intentó primario (None) y cayó al verificador (glm-test).
    assert llamadas == [None, "glm-test"]


def test_mensaje_si_toda_la_cascada_falla(monkeypatch):
    def fake_chat(prompt, max_tokens=600, temperature=0.6, json=False, model=None):
        raise RuntimeError("todo caido")

    monkeypatch.setattr(dm, "groq_disponible", lambda: True)
    monkeypatch.setattr(dm, "chat_texto", fake_chat)
    monkeypatch.setattr(dm, "VERIFIER_MODEL", "glm-test")
    _limpiar_cache()

    out = dm.generar_narrativa_ia("brecha", {"score": 0.333, "n": 3})
    assert "no disponible" in out.lower()


def test_sin_proveedor_no_llama_modelo(monkeypatch):
    monkeypatch.setattr(dm, "groq_disponible", lambda: False)
    _limpiar_cache()

    out = dm.generar_narrativa_ia("leccion", {"score": 0.444, "n": 4})
    assert "no disponible" in out.lower()
