"""Tests para analytics/schema_validator.py (T4.2)."""
import pytest
from analytics.schema_validator import validar, ValidationError, ValidationResult


def _base_valid():
    """analysis.json minimo que pasa todas las validaciones."""
    return {
        "meta": {
            "periodo": "2026-04",
            "fecha_datos_hasta": "2026-04-30",
            "generado_en": "2026-05-01T10:00:00",
        },
        "bloque1": {
            "clima_narrativo": {
                "narrativa": "Clima estable.",
                "enlaces_referencia": [],
            },
            "indice_emociones": {
                "emocion_dominante": "calma",
                "narrativa": "",
                "enlaces_referencia": [],
            },
            "intensidad": {"narrativa": "", "enlaces_referencia": []},
            "concentracion_tematica": {
                "ramas": [
                    {"tema": "seguridad", "share": 50.0, "emocion_dominante": "calma"},
                    {"tema": "movilidad", "share": 50.0, "emocion_dominante": "calma"},
                ],
                "narrativa": "",
                "enlaces_referencia": [],
            },
            "pulso_iq": {"narrativa": "", "enlaces_referencia": []},
            "metricas_rendimiento": {"narrativa": "", "enlaces_referencia": []},
        },
        "bloque2": {
            "voces_influencia": [
                {
                    "pagina": "Alcaldía",
                    "postura": "apoyo",
                    "engagement": 1500,
                    "reacciones_totales": 1000,
                    "comentarios_totales": 300,
                    "compartidos_totales": 200,
                    "narrativa": "",
                    "enlaces_referencia": [],
                },
            ],
        },
        "bloque3": {
            "puntos_friccion": [
                {
                    "tema": "seguridad",
                    "n_negativos": 45,
                    "emocion_dominante": "enojo",
                    "citas_moderadas": [],
                    "narrativa": "",
                    "enlaces_relacionados": [],
                },
            ],
            "autenticidad": {"narrativa": "", "enlaces_referencia": []},
            "velocidad_propagacion": {"narrativa": "", "enlaces_referencia": []},
            "nivel_alerta": {"alertas_cambridge": [], "narrativa": "", "enlaces_referencia": []},
        },
        "bloque4": {
            "eco_historico": {"narrativa": "", "enlaces_referencia": []},
            "leccion_aprendida": {"narrativa": "", "enlaces_referencia": []},
            "brecha_percepcion_realidad": {"narrativa": "", "enlaces_referencia": []},
            "contexto_no_visible": {"narrativa": "", "enlaces_referencia": []},
            "correlacion_contenido_reaccion": {"narrativa": "", "enlaces_referencia": []},
            "comparativa_sectorial": {"narrativa": "", "enlaces_referencia": []},
            "proyeccion_escenario": {"narrativa": "", "enlaces_referencia": []},
            "recomendacion_estrategica": {"narrativa": "", "enlaces_referencia": []},
        },
    }


def test_valido_base_es_publicable():
    r = validar(_base_valid())
    assert r.es_publicable
    assert len(r.errores) == 0


def test_no_es_dict():
    r = validar("no soy dict")
    assert not r.es_publicable
    assert r.errores[0].codigo == "V00_NO_ES_DICT"


# ── V01 ──
def test_v01_engagement_sin_submetricas():
    d = _base_valid()
    d["bloque2"]["voces_influencia"][0]["reacciones_totales"] = 0
    d["bloque2"]["voces_influencia"][0]["comentarios_totales"] = 0
    d["bloque2"]["voces_influencia"][0]["compartidos_totales"] = 0
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V01_ENGAGEMENT_SIN_SUBMETRICAS" for e in r.errores)


def test_v01_engagement_ok_con_submetricas():
    d = _base_valid()
    r = validar(d)
    assert not any(e.codigo == "V01_ENGAGEMENT_SIN_SUBMETRICAS" for e in r.errores)


# ── V02 ──
def test_v02_shares_no_suman_100():
    d = _base_valid()
    d["bloque1"]["concentracion_tematica"]["ramas"][0]["share"] = 30
    d["bloque1"]["concentracion_tematica"]["ramas"][1]["share"] = 30
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V02_SHARES_TEMATICA_NO_SUMAN_100" for e in r.errores)


def test_v02_shares_suman_100():
    r = validar(_base_valid())
    assert not any(e.codigo == "V02_SHARES_TEMATICA_NO_SUMAN_100" for e in r.errores)


# ── V03 ──
def test_v03_friccion_sin_emocion():
    d = _base_valid()
    d["bloque3"]["puntos_friccion"][0]["emocion_dominante"] = ""
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V03_FRICCION_SIN_EMOCION" for e in r.errores)


# ── V04 ──
def test_v04_alerta_descripcion_dict():
    d = _base_valid()
    d["bloque3"]["nivel_alerta"]["alertas_cambridge"] = [
        {"tipo": "rumor", "descripcion": {"verdadero": True}},
    ]
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V04_ALERTA_DESCRIPCION_MAL_TIPADA" for e in r.errores)


def test_v04_alerta_ok():
    d = _base_valid()
    d["bloque3"]["nivel_alerta"]["alertas_cambridge"] = [
        {"tipo": "rumor", "descripcion": "Hay un rumor circulando."},
    ]
    r = validar(d)
    assert not any(e.codigo == "V04_ALERTA_DESCRIPCION_MAL_TIPADA" for e in r.errores)


# ── V05 ──
def test_v05_bloque4_mal_tipado():
    d = _base_valid()
    d["bloque4"]["eco_historico"] = "no soy dict"
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V05_BLOQUE4_MAL_TIPADO" for e in r.errores)


# ── V06 ──
def test_v06_meta_periodo_incompleto():
    d = _base_valid()
    d["meta"]["periodo"] = ""
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V06_META_PERIODO_INCOMPLETO" for e in r.errores)


def test_v06_meta_falta_generado_en():
    d = _base_valid()
    d["meta"]["generado_en"] = ""
    r = validar(d)
    assert not r.es_publicable


# ── V07 ──
def test_v07_emocion_desconocida():
    d = _base_valid()
    d["bloque1"]["indice_emociones"]["emocion_dominante"] = "super_feliz"
    r = validar(d)
    assert r.es_publicable  # advertencia, no bloqueante (catálogo abierto)
    assert any(e.codigo == "V07_EMOCION_NO_CANONICA" for e in r.errores)


def test_v07_postura_desconocida():
    d = _base_valid()
    d["bloque2"]["voces_influencia"][0]["postura"] = "neutra_total"
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V07_CATEGORIA_DESCONOCIDA" for e in r.errores)


def test_v07_tema_desconocido():
    d = _base_valid()
    d["bloque1"]["concentracion_tematica"]["ramas"][0]["tema"] = "tema_fantasma"
    r = validar(d)
    assert r.es_publicable  # tema no-canónico es advertencia (V11), no bloqueante


# ── V08 ──
def test_v08_narrativa_cita_cifras_sin_enlaces():
    d = _base_valid()
    d["bloque1"]["clima_narrativo"]["narrativa"] = "Hay 150 comentarios negativos."
    d["bloque1"]["clima_narrativo"]["enlaces_referencia"] = []
    r = validar(d)
    assert r.es_publicable  # advertencia, no bloqueante
    assert any(e.codigo == "V08_NARRATIVA_SIN_ENLACES" for e in r.errores)


def test_v08_narrativa_con_enlaces_ok():
    d = _base_valid()
    d["bloque1"]["clima_narrativo"]["narrativa"] = "Hay 150 comentarios negativos."
    d["bloque1"]["clima_nistrativa"] = {"narrativa": "", "enlaces_referencia": []}
    d["bloque1"]["clima_narrativo"]["enlaces_referencia"] = ["https://ejemplo.com"]
    r = validar(d)
    assert not any(e.codigo == "V08_NARRATIVA_SIN_ENLACES" for e in r.errores)


# ── V09 ──
def test_v09_placeholder_sin_resolver():
    d = _base_valid()
    d["bloque1"]["clima_narrativo"]["narrativa"] = "La seguridad tiene {tema_share_seguridad}%"
    r = validar(d)
    assert r.es_publicable  # advertencia, no bloqueante
    assert any(e.codigo == "V09_PLACEHOLDER_SIN_RESOLVER" for e in r.errores)


def test_v09_narrativa_sin_placeholders():
    d = _base_valid()
    d["bloque1"]["clima_narrativo"]["narrativa"] = "Narrativa sin placeholders."
    r = validar(d)
    assert not any(e.codigo == "V09_PLACEHOLDER_SIN_RESOLVER" for e in r.errores)


def test_v09_narrativa_vacia():
    d = _base_valid()
    d["bloque1"]["clima_narrativo"]["narrativa"] = ""
    r = validar(d)
    assert not any(e.codigo == "V09_PLACEHOLDER_SIN_RESOLVER" for e in r.errores)


# ── V10 ──
def test_v10_valor_negativo():
    d = _base_valid()
    d["bloque2"]["voces_influencia"][0]["engagement"] = -5
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V10_VALOR_NEGATIVO" for e in r.errores)


def test_v10_engagement_sin_submetricas():
    d = _base_valid()
    d["bloque2"]["voces_influencia"][0]["reacciones_totales"] = 0
    d["bloque2"]["voces_influencia"][0]["comentarios_totales"] = 0
    d["bloque2"]["voces_influencia"][0]["compartidos_totales"] = 0
    r = validar(d)
    assert not r.es_publicable  # V01 catches this as bloqueante


def test_v10_share_negativo():
    d = _base_valid()
    d["bloque1"]["concentracion_tematica"]["ramas"][0]["share"] = -10
    r = validar(d)
    assert not r.es_publicable
    assert any(e.codigo == "V10_SHARE_NEGATIVO" for e in r.errores)


# ── V11 ──
def test_v11_tema_no_valido():
    d = _base_valid()
    d["bloque1"]["concentracion_tematica"]["ramas"][0]["tema"] = "tema_inventado"
    r = validar(d)
    assert any(e.codigo == "V11_TEMA_NO_VALIDO" for e in r.errores)


def test_v11_tema_valido():
    d = _base_valid()
    r = validar(d)
    assert not any(e.codigo == "V11_TEMA_NO_VALIDO" for e in r.errores)


# ── ValidationResult helpers ──
def test_validation_result_bloqueantes():
    r = ValidationResult()
    r.errores.append(ValidationError("X", "y", "bloqueante", "t", "h"))
    r.errores.append(ValidationError("Z", "w", "advertencia", "t", "h"))
    assert not r.es_publicable
    assert len(r.bloqueantes()) == 1
    assert len(r.advertencias()) == 1
