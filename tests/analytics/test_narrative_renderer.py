"""Tests para analytics/narrative_renderer.py (T6.1)."""
import pytest
from analytics.narrative_renderer import (
    renderizar_narrativa, renderizar_narrativas_seccion,
    construir_contexto, renderizar_analysis,
)


def test_renderizar_basico():
    ctx = {"total": 100, "nombre": "seguridad"}
    result = renderizar_narrativa("Hay {total} comentarios en {nombre}.", ctx)
    assert result == "Hay 100 comentarios en seguridad."


def test_renderizar_float():
    ctx = {"share": 45.678}
    result = renderizar_narrativa("Share: {share}%", ctx)
    assert result == "Share: 45.7%"


def test_renderizar_placeholder_desconocido_se_mantiene():
    ctx = {"x": 1}
    result = renderizar_narrativa("Hola {y} mundo", ctx)
    assert result == "Hola {y} mundo"


def test_renderizar_texto_vacio():
    assert renderizar_narrativa("", {}) == ""
    assert renderizar_narrativa(None, {}) is None


def test_renderizar_narrativas_seccion():
    sec = {"narrativa": "Hay {total} docs.", "enlaces_referencia": []}
    result = renderizar_narrativas_seccion(sec, {"total": 42})
    assert result["narrativa"] == "Hay 42 docs."
    assert result["enlaces_referencia"] == []


def test_renderizar_citas_moderadas():
    sec = {
        "narrativa": "",
        "citas_moderadas": ["Cita {tema}", "Otra {x}"],
    }
    result = renderizar_narrativas_seccion(sec, {"tema": "seg", "x": 5})
    assert result["citas_moderadas"] == ["Cita seg", "Otra 5"]


def test_construir_contexto_emociones():
    analysis = {
        "meta": {"periodo": "2026-04", "fecha_datos_hasta": "2026-04-30"},
        "bloque1": {
            "indice_emociones": {
                "emocion_dominante": "alegria",
                "pct_alegria": 45.5,
                "pct_tristeza": 20.0,
            },
            "concentracion_tematica": {
                "ramas": [{"tema": "seguridad", "share": 60.0, "emocion_dominante": "tristeza"}],
                "nivel": "dominado",
            },
        },
        "bloque2": {
            "voces_influencia": [
                {"pagina": "Alcaldia", "engagement": 1000, "reacciones_totales": 500,
                 "comentarios_totales": 300, "compartidos_totales": 200},
            ],
            "polarizacion": {"nivel": "dividida"},
        },
        "bloque3": {
            "puntos_friccion": [
                {"tema": "seguridad", "n_negativos": 45, "n_comentarios_total": 500},
            ],
        },
    }
    ctx = construir_contexto(analysis)
    assert ctx["periodo"] == "2026-04"
    assert ctx["fecha_hasta"] == "2026-04-30"
    assert ctx["emocion_dominante"] == "alegria"
    assert ctx["emocion_alegria_pct"] == 45.5
    assert ctx["tema_share_seguridad"] == 60.0
    assert ctx["concentracion_nivel"] == "dominado"
    assert ctx["polarizacion_nivel"] == "dividida"
    assert ctx["total_aprobados"] == 1000
    assert ctx["friccion_seguridad_negativos"] == 45


def test_renderizar_analysis_completo():
    analysis = {
        "meta": {"periodo": "2026-04", "fecha_datos_hasta": "2026-04-30"},
        "bloque1": {
            "clima_narrativo": {"narrativa": "Periodo: {periodo}", "enlaces_referencia": []},
            "indice_emociones": {"emocion_dominante": "calma", "narrativa": "", "enlaces_referencia": []},
            "intensidad": {"narrativa": "", "enlaces_referencia": []},
            "concentracion_tematica": {
                "ramas": [], "nivel": "fragmentado",
                "narrativa": "", "enlaces_referencia": [],
            },
            "pulso_iq": {"narrativa": "", "enlaces_referencia": []},
            "metricas_rendimiento": {"narrativa": "", "enlaces_referencia": []},
        },
        "bloque2": {"voces_influencia": [], "polarizacion": {"nivel": "consenso", "narrativa": "", "enlaces_referencia": []}},
        "bloque3": {
            "puntos_friccion": [],
            "autenticidad": {"narrativa": "", "enlaces_referencia": []},
            "velocidad_propagacion": {"narrativa": "", "enlaces_referencia": []},
            "nivel_alerta": {"alertas_cambridge": [], "narrativa": "", "enlaces_referencia": []},
        },
        "bloque4": {
            "eco_historico": {"narrativa": "En {periodo} paso...", "enlaces_referencia": []},
        },
    }
    result = renderizar_analysis(analysis)
    assert result["bloque1"]["clima_narrativo"]["narrativa"] == "Periodo: 2026-04"
    assert result["bloque4"]["eco_historico"]["narrativa"] == "En 2026-04 paso..."
