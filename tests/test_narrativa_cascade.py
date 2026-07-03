"""Tests de la cascada de generación narrativa del Bloque IV.

Verifican que generar_narrativa_ia (dashboard/dash_metrics.py) use la cascada
NIM: primario DeepSeek y, si falla, respaldo con el verificador GLM. No se toca
la red: chat_texto se inyecta como un fake mediante monkeypatch.

Tests para D4: validación anti-mezcla enojo/crítico en dash_narrativa.generar_narrativa.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import dashboard.dash_metrics as dm
import dashboard.dash_narrativa as dn


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


# ── D4: Validación anti-mezcla enojo/crítico ──


def _limpiar_cache_narrativa():
    # Limpiar cache de generar_narrativa (dash_narrativa.py) - no usa st.cache_data
    # sino cache interno _CACHE
    with dn._LOCK:
        dn._CACHE.clear()


def test_compara_enojo_critico_misma_oracion_detecta():
    """Misma oración con 'enojo' y 'crítico' → detectado (True)."""
    texto = "El enojo de las reacciones es menor que el 38% crítico de los comentarios."
    assert dn._compara_enojo_critico(texto) is True


def test_compara_enojo_critico_oraciones_distintas_no_detecta():
    """'enojo' y 'crítico' en oraciones distintas → NO detectado (False)."""
    texto = "El índice de enojo es bajo. El porcentaje crítico de comentarios es alto."
    assert dn._compara_enojo_critico(texto) is False


def test_compara_enojo_critico_variantes_enoja_critica_detecta():
    """Variantes 'enoja' y 'crítica' en misma oración → detectado."""
    texto = "Lo que enoja a la gente no es lo mismo que el 40% crítica en los textos."
    assert dn._compara_enojo_critico(texto) is True


def test_compara_enojo_critico_plural_criticos_detecta():
    """Plural 'críticos' en misma oración que 'enojo' → detectado."""
    texto = "El enojo de las reacciones no equivale al 38% de comentarios críticos."
    assert dn._compara_enojo_critico(texto) is True


def test_generar_narrativa_reintenta_si_viola_regla(monkeypatch):
    """Mock: primera respuesta viola regla, segunda respeta → devuelve la corregida."""
    llamadas = []

    def fake_chat(prompt, max_tokens=600, temperature=0.5, json=False, model=None):
        llamadas.append(1)
        if len(llamadas) == 1:
            # Primera respuesta: VIOLA regla (enojo + crítico en misma oración)
            return "El enojo de las reacciones es menor que el 30% crítico de comentarios.", "stop", None
        # Segunda respuesta (reintento): respeta la regla - enojo y crítico en oraciones distintas
        return "El índice de enojo es 0.4%. Los comentarios críticos son el 30%.", "stop", None

    monkeypatch.setattr(dn, "chat_texto", fake_chat)
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    out = dn.generar_narrativa("recomendacion", {"score": 0.1, "n": 10})
    # Debe devolver la SEGUNDA respuesta (la corregida)
    assert "índice de enojo" in out.lower()
    # Verificar que no viola la regla (enojo y crítico en oraciones distintas = OK)
    assert dn._compara_enojo_critico(out) is False


def test_generar_narrativa_dos_violaciones_cae_fallback(monkeypatch):
    """Mock: ambas respuestas violan la regla → devuelve _FALLBACK."""
    llamadas = []

    def fake_chat(prompt, max_tokens=600, temperature=0.5, json=False, model=None):
        llamadas.append(1)
        # Ambas violan la regla
        return "El enojo es menor que el 40% crítico de los comentarios.", "stop", None

    monkeypatch.setattr(dn, "chat_texto", fake_chat)
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    out = dn.generar_narrativa("recomendacion", {"score": 0.1, "n": 10})
    # Debe caer a _FALLBACK
    assert out == dn._FALLBACK
    assert len(llamadas) == 2


def test_generar_narrativa_verificador_tambien_valida_regla(monkeypatch):
    """Si primario falla y verificador responde pero viola regla → fallback."""
    llamadas = []

    def fake_chat(prompt, max_tokens=600, temperature=0.5, json=False, model=None):
        llamadas.append(model)
        if model is None:
            raise RuntimeError("primario caido")
        # Verificador responde pero viola la regla
        return "El enojo supera el 50% crítico según los comentarios.", "stop", None

    monkeypatch.setattr(dn, "chat_texto", fake_chat)
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", "glm-test")
    _limpiar_cache_narrativa()

    out = dn.generar_narrativa("eco_historico", {"score": 0.2, "n": 5})
    assert out == dn._FALLBACK
    # Intentó primario (None) y verificador (glm-test)
    assert llamadas == [None, "glm-test"]
