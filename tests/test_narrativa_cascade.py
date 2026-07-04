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


# ── D7: Validación de saldo (_contradice_saldo) ──


def test_contradice_saldo_positivo_texto_critico_detecta():
    """Saldo real positivo (+40) pero texto dice 'predominio crítico' → True."""
    ctx = {"pct_favorable": 60, "pct_critico": 20}
    texto = "Hay un predominio crítico en los comentarios de la semana."
    assert dn._contradice_saldo(texto, ctx) is True


def test_contradice_saldo_negativo_texto_favorable_detecta():
    """Saldo real negativo (-40) pero texto dice 'apoyo mayoritario' → True."""
    ctx = {"pct_favorable": 20, "pct_critico": 60}
    texto = "Se observa un apoyo mayoritario de la ciudadanía."
    assert dn._contradice_saldo(texto, ctx) is True


def test_contradice_saldo_coincide_no_dispara():
    """Saldo positivo (+40) y texto dice 'mayoría favorable' → False."""
    ctx = {"pct_favorable": 60, "pct_critico": 20}
    texto = "La mayoría favorable de comentarios supera a los críticos."
    assert dn._contradice_saldo(texto, ctx) is False


def test_contradice_saldo_correlacion_sin_campos_nunca_dispara():
    """Tipo 'correlacion' no tiene pct_favorable/pct_critico → siempre False."""
    ctx = {"rango": "ene-2024", "correlacion": {"x": 1}}
    texto = "predominio crítico en los datos analizados"
    assert dn._contradice_saldo(texto, ctx) is False


def test_generar_narrativa_reintenta_si_contradice_saldo(monkeypatch):
    """Mock: primera respuesta contradice saldo, segunda respeta → devuelve la corregida."""
    llamadas = []

    def fake_chat(prompt, max_tokens=600, temperature=0.5, json=False, model=None):
        llamadas.append(1)
        if len(llamadas) == 1:
            return "Hay un apoyo mayoritario de la ciudadanía hacia la gestión.", "stop", None
        return "Los comentarios críticos son mayoría. Los favorables son minoría.", "stop", None

    monkeypatch.setattr(dn, "chat_texto", fake_chat)
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    out = dn.generar_narrativa("recomendacion", {"pct_favorable": 20, "pct_critico": 60, "score": 0.1, "n": 10})
    assert "críticos son mayoría" in out.lower()
    assert dn._contradice_saldo(out, {"pct_favorable": 20, "pct_critico": 60}) is False


def test_generar_narrativa_dos_violaciones_saldo_cae_fallback(monkeypatch):
    """Mock: ambas respuestas contradicen saldo → devuelve _FALLBACK."""
    llamadas = []

    def fake_chat(prompt, max_tokens=600, temperature=0.5, json=False, model=None):
        llamadas.append(1)
        return "Hay un apoyo mayoritario de la ciudadanía hacia la gestión.", "stop", None

    monkeypatch.setattr(dn, "chat_texto", fake_chat)
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    out = dn.generar_narrativa("recomendacion", {"pct_favorable": 20, "pct_critico": 60, "score": 0.1, "n": 10})
    assert out == dn._FALLBACK
    assert len(llamadas) == 2


# ── D6: Filtrado de contexto por estación + corrección prompt "contexto" ──

def test_prompt_contexto_no_contiene_picos_actividad():
    """El prompt de 'contexto' en _PROMPTS ya no contiene 'picos de actividad'."""
    prompt = dn._PROMPTS["contexto"]
    assert "picos de actividad" not in prompt.lower()
    assert "temas dominantes" in prompt
    assert "zonas con más enojo" in prompt


def _fake_chat_capture(prompts_captured):
    """Factory que captura el prompt pasado a chat_texto."""
    def fake(prompt, max_tokens=600, temperature=0.5, json=False, model=None):
        prompts_captured.append(prompt)
        return "Texto válido sin violar regla. Enojo bajo. Críticos altos.", "stop", None
    return fake


def test_generar_narrativa_correlacion_no_ve_temas_ni_indice_enojo(monkeypatch):
    """Tipo 'correlacion' NO ve temas_que_funcionaron, temas_con_rechazo, indice_enojo."""
    prompts_captured = []
    monkeypatch.setattr(dn, "chat_texto", _fake_chat_capture(prompts_captured))
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    ctx_completo = {
        "rango": "2024-01-01 a 2024-01-31",
        "correlacion": {"publicaciones_analizadas": 10, "promedio_interacciones": 150},
        "temas_que_funcionaron": ["tema1", "tema2"],
        "temas_con_rechazo": ["tema3"],
        "indice_enojo": 0.05,
        "pct_critico": 30,
        "comentarios_analizados": 500,
    }
    dn.generar_narrativa("correlacion", ctx_completo)

    assert len(prompts_captured) == 1
    prompt = prompts_captured[0]
    assert "temas_que_funcionaron" not in prompt
    assert "temas_con_rechazo" not in prompt
    assert "indice_enojo" not in prompt
    assert "correlacion" in prompt
    assert "publicaciones_analizadas" in prompt


def test_generar_narrativa_contexto_no_ve_correlacion(monkeypatch):
    """Tipo 'contexto' NO ve la clave 'correlacion' ni sus subcampos."""
    prompts_captured = []
    monkeypatch.setattr(dn, "chat_texto", _fake_chat_capture(prompts_captured))
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    ctx_completo = {
        "comentarios_analizados": 500,
        "pct_critico": 30,
        "indice_enojo": 0.05,
        "temas_que_funcionaron": ["tema1"],
        "temas_con_rechazo": ["tema2"],
        "correlacion": {"publicaciones_analizadas": 10, "promedio_interacciones": 150},
        "pct_favorable": 40,
        "pct_neutral": 30,
    }
    dn.generar_narrativa("contexto", ctx_completo)

    assert len(prompts_captured) == 1
    prompt = prompts_captured[0]
    assert "correlacion" not in prompt
    assert "publicaciones_analizadas" not in prompt
    assert "promedio_interacciones" not in prompt
    # Pero sí ve sus campos permitidos
    assert "comentarios_analizados" in prompt
    assert "pct_critico" in prompt
    assert "indice_enojo" in prompt
    assert "temas_que_funcionaron" in prompt
    assert "temas_con_rechazo" in prompt


def test_generar_narrativa_brecha_recibe_sus_campos_esperados(monkeypatch):
    """Tipo 'brecha' SÍ recibe pct_favorable, indice_enojo, temas_que_funcionaron, etc."""
    prompts_captured = []
    monkeypatch.setattr(dn, "chat_texto", _fake_chat_capture(prompts_captured))
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    ctx_completo = {
        "comentarios_analizados": 500,
        "pct_favorable": 45,
        "pct_neutral": 25,
        "pct_critico": 30,
        "indice_enojo": 0.04,
        "temas_que_funcionaron": ["tema1"],
        "temas_con_rechazo": ["tema2"],
        "temas_emergentes": ["tema3"],  # no debería ver esto
        "correlacion": {"x": 1},  # no debería ver esto
    }
    dn.generar_narrativa("brecha", ctx_completo)

    assert len(prompts_captured) == 1
    prompt = prompts_captured[0]
    # Campos permitidos para brecha
    assert "comentarios_analizados" in prompt
    assert "pct_favorable" in prompt
    assert "pct_neutral" in prompt
    assert "pct_critico" in prompt
    assert "indice_enojo" in prompt
    assert "temas_que_funcionaron" in prompt
    assert "temas_con_rechazo" in prompt
    # Campos NO permitidos para brecha
    assert "temas_emergentes" not in prompt
    assert "correlacion" not in prompt


def test_generar_narrativa_cache_key_usa_ctx_filtrado(monkeypatch):
    """La clave de caché usa el ctx FILTRADO (no el completo)."""
    prompts_captured = []
    call_count = [0]

    def fake_chat(prompt, max_tokens=600, temperature=0.5, json=False, model=None):
        call_count[0] += 1
        prompts_captured.append(prompt)
        return "Texto válido.", "stop", None

    monkeypatch.setattr(dn, "chat_texto", fake_chat)
    monkeypatch.setattr(dn, "groq_disponible", lambda: True)
    monkeypatch.setattr(dn, "VERIFIER_MODEL", None)
    _limpiar_cache_narrativa()

    ctx_base = {
        "comentarios_analizados": 500,
        "pct_critico": 30,
        "indice_enojo": 0.05,
        "temas_que_funcionaron": ["tema1"],
        "temas_con_rechazo": ["tema2"],
        "correlacion": {"publicaciones_analizadas": 10},  # solo para contexto
    }
    # Primera llamada: tipo "contexto" filtra correlacion
    dn.generar_narrativa("contexto", ctx_base)
    # Segunda llamada: MISMO ctx_base completo, pero tipo "correlacion" filtra distinto
    # Si la cache key usara el ctx completo (sin filtrar), colisionarían y
    # la segunda llamada usaría cache de la primera (mal). Deben ser keys distintas.
    dn.generar_narrativa("correlacion", ctx_base)

    # Deben ser DOS llamadas distintas (no cache hit)
    assert call_count[0] == 2
    # Verificar que los prompts son distintos (diferentes campos filtrados)
    assert "correlacion" not in prompts_captured[0]  # contexto no ve correlacion
    assert "correlacion" in prompts_captured[1]      # correlacion sí ve correlacion
