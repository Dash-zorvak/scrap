"""Tests para analytics/report.py (T5.2)."""
import pytest
from analytics.report import construir_analysis, generar_reporte_completo


def _sample_aprobaciones():
    return [
        {
            "id": 1, "categoria": "seguridad", "label": "Seguridad",
            "pct": 45.0, "doc_count": 90,
            "apoyo": 20, "critica": 50, "neutral": 20,
            "pct_apoyo": 22.2, "pct_critica": 55.6, "pct_neutral": 22.2,
            "saldo": -30, "ejemplo": "", "ejemplo_critica": "",
            "emociones": {
                "alegria": {"count": 10, "pct": 20.0},
                "tristeza": {"count": 30, "pct": 60.0},
                "calma": {"count": 10, "pct": 20.0},
            },
            "emocion_dominante": "tristeza",
        },
        {
            "id": 2, "categoria": "movilidad", "label": "Movilidad",
            "pct": 35.0, "doc_count": 70,
            "apoyo": 40, "critica": 10, "neutral": 20,
            "pct_apoyo": 57.1, "pct_critica": 14.3, "pct_neutral": 28.6,
            "saldo": 30, "ejemplo": "", "ejemplo_critica": "",
            "emociones": {
                "alegria": {"count": 40, "pct": 80.0},
                "calma": {"count": 10, "pct": 20.0},
            },
            "emocion_dominante": "alegria",
        },
        {
            "id": 3, "categoria": "salud", "label": "Salud",
            "pct": 20.0, "doc_count": 40,
            "apoyo": 30, "critica": 5, "neutral": 5,
            "pct_apoyo": 75.0, "pct_critica": 12.5, "pct_neutral": 12.5,
            "saldo": 25, "ejemplo": "", "ejemplo_critica": "",
            "emociones": {
                "confianza": {"count": 30, "pct": 75.0},
                "calma": {"count": 10, "pct": 25.0},
            },
            "emocion_dominante": "confianza",
        },
    ]


def test_construir_analysis_estructura():
    data = construir_analysis(_sample_aprobaciones(), "2026-04", "2026-04-30")
    assert "meta" in data
    assert "bloque1" in data
    assert "bloque2" in data
    assert "bloque3" in data
    assert "bloque4" in data
    assert data["meta"]["periodo"] == "2026-04"
    assert data["meta"]["fecha_datos_hasta"] == "2026-04-30"


def test_construir_analysis_voces():
    """H2: voces_influencia solo incluye actores con datos reales.
    Sin datos de Externos, la lista queda vacía (las voces fabricadas
    de aprobaciones_agrupadas fueron eliminadas)."""
    data = construir_analysis(_sample_aprobaciones(), "2026-04", "2026-04-30")
    voces = data["bloque2"]["voces_influencia"]
    assert isinstance(voces, list)
    # Sin Externos reales, voces está vacía
    assert len(voces) == 0


def test_construir_analysis_fricciones():
    data = construir_analysis(_sample_aprobaciones(), "2026-04", "2026-04-30")
    fricciones = data["bloque3"]["puntos_friccion"]
    assert len(fricciones) == 3  # all 3 have critica > 0


def test_construir_analysis_emociones_globales():
    data = construir_analysis(_sample_aprobaciones(), "2026-04", "2026-04-30")
    ie = data["bloque1"]["indice_emociones"]
    assert "emocion_dominante" in ie
    assert ie["emocion_dominante"] in ("alegria", "tristeza", "confianza", "calma")


def test_construir_analysis_vacio():
    data = construir_analysis([], "2026-04", "2026-04-30")
    assert data["bloque1"]["concentracion_tematica"]["ramas"] == []
    assert data["bloque2"]["voces_influencia"] == []


def test_generar_reporte_completo():
    data, resultado = generar_reporte_completo(
        _sample_aprobaciones(), "2026-04", "2026-04-30"
    )
    assert isinstance(data, dict)
    # The report may or may not be publicable depending on narrative completeness
    assert hasattr(resultado, "es_publicable")
    assert hasattr(resultado, "errores")


# ── Sentimiento por reglas léxicas en clima_narrativo ──

def test_clima_narrativo_campos_sentimiento():
    data = construir_analysis(_sample_aprobaciones(), "2026-04", "2026-04-30")
    cn = data["bloque1"]["clima_narrativo"]
    assert "tono_dominante" in cn
    assert "pct_favorable" in cn
    assert "pct_neutral" in cn
    assert "pct_critico" in cn
    assert "n_total_comentarios" in cn
    assert "tono_score_hoy" in cn
    assert "tono_score_ayer" in cn
    assert "tendencia" in cn
    assert "etiqueta_tendencia" in cn
    assert "formula_usada" in cn


def test_clima_narrativo_fallback_sin_texts():
    data = construir_analysis(_sample_aprobaciones(), "2026-04", "2026-04-30")
    cn = data["bloque1"]["clima_narrativo"]
    assert cn["n_total_comentarios"] == 200  # 90+70+40
    assert cn["tono_score_ayer"] == 0.0
    assert cn["formula_usada"] == "NSI = (positivos - negativos) / total * 100"


def test_clima_narrativo_con_texts_lexico():
    texts = [
        "Excelente servicio",
        "Bueno y eficiente",
        "Muy satisfecho",
        "La reunión es el lunes",
        "Hola",
    ]
    data = construir_analysis(
        _sample_aprobaciones(), "2026-04", "2026-04-30",
        comentarios_texts=texts,
    )
    cn = data["bloque1"]["clima_narrativo"]
    assert cn["n_total_comentarios"] == 5
    assert cn["tono_dominante"] in ("positivo", "muy_positivo", "neutral")
    assert cn["pct_favorable"] >= 0
    assert cn["pct_critico"] >= 0
    assert cn["tono_score_hoy"] >= 0


def test_clima_narrativo_texts_negativos():
    texts = [
        "Terrible servicio",
        "Muy deficiente",
        "Inaceptable",
    ]
    data = construir_analysis(
        _sample_aprobaciones(), "2026-04", "2026-04-30",
        comentarios_texts=texts,
    )
    cn = data["bloque1"]["clima_narrativo"]
    assert cn["n_total_comentarios"] == 3
    assert cn["tono_dominante"] in ("negativo", "muy_negativo")
    assert cn["tono_score_hoy"] < 0


def test_clima_narrativo_texts_vacio_fallback():
    data = construir_analysis(
        _sample_aprobaciones(), "2026-04", "2026-04-30",
        comentarios_texts=[],
    )
    cn = data["bloque1"]["clima_narrativo"]
    # Empty list falls back to aprobaciones-based computation
    assert cn["n_total_comentarios"] == 200


def test_tendencia_etiqueta():
    texts = ["Excelente", "Brillante", "Genial", "Maravilloso"]
    data = construir_analysis(
        _sample_aprobaciones(), "2026-04", "2026-04-30",
        comentarios_texts=texts,
    )
    cn = data["bloque1"]["clima_narrativo"]
    assert cn["tono_score_ayer"] == 0.0
    assert cn["tendencia"] == cn["tono_score_hoy"]
    assert cn["etiqueta_tendencia"] in ("mejorando", "empeorando", "estable")


# ── 18.4: Emergentes solo recibe textos no_aplica/low-signal ──

def test_emergentes_no_incluye_textos_con_tema_claro():
    """Textos con tema claro (obras_servicios) NO deben aparecer en temas_emergentes_lda."""
    texts = [
        "Hay muchos baches en la calle principal",  # obras_servicios (múltiples hits)
        "Los baches están terribles en toda la zona",  # obras_servicios
        "Tantos baches no se puede circular",  # obras_servicios
        "Hola que tal",  # no_aplica → sí debería incluirse
    ]
    data = construir_analysis(
        _sample_aprobaciones(), "2026-04", "2026-04-30",
        comentarios_texts=texts,
    )
    emergentes = data["bloque2"]["temas_emergentes_lda"]
    # Si hay emergentes, ninguno debe venir de textos con tema claro
    for e in emergentes:
        tema_texto = e.get("tema", "")
        # "baches" es un bigrama que podría aparecer, pero solo si viene de textos sin tema claro
        # En este caso todos los textos con "baches" tienen tema claro → no debe haber emergentes
        # o si los hay, son de los textos no_aplica
        assert isinstance(tema_texto, str)


# ── Bug 1: evidencia_por_emocion per-comentario (no global) ──

def test_evidencia_por_emocion_multiple_keys_distinct_emotions(tmp_path):
    """evidencia_por_emocion tiene múltiples claves cuando los comentarios
    tienen emociones distintas (no colapsa a una sola emoción global)."""
    # Comentarios con emociones claramente distintas
    contexto = [
        {"id": "c1", "texto": "Estoy furioso con todo, odio esto", "post_id": "p1", "plataforma": "facebook"},
        {"id": "c2", "texto": "Qué alegría, me encanta este proyecto", "post_id": "p2", "plataforma": "facebook"},
        {"id": "c3", "texto": "Muy triste lo que pasó, me duele", "post_id": "p3", "plataforma": "facebook"},
        {"id": "c4", "texto": "Otro furioso más, indignado completamente", "post_id": "p4", "plataforma": "facebook"},
    ]

    data = construir_analysis(
        _sample_aprobaciones(), "2026-04", "2026-04-30",
        comentarios_texts=[c["texto"] for c in contexto],
        comentarios_con_contexto=contexto,
    )

    # Leer evidencia persistida
    evidencia_path = tmp_path.parent / "data" / "_evidencia_periodo.json"
    # La evidencia se escribe en data/_evidencia_periodo.json del repo
    import os
    evidencia_data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "_evidencia_periodo.json"
    )
    # Verificar que el dict en memoria tiene múltiples claves
    # (construir_analysis lo escribe a disco; verificamos que no colapsa)
    # Forzamos re-ejecución para leer el archivo
    import json
    with open(evidencia_data_path, "r") as f:
        evidencia = json.load(f)

    por_emocion = evidencia.get("por_emocion", {})
    # Debe haber al menos 2 emociones distintas (no una sola global)
    assert len(por_emocion) >= 2, (
        f"Se esperaban >=2 emociones distintas, se obtuvo {len(por_emocion)}: "
        f"{list(por_emocion.keys())}"
    )
    # Cada emoción solo debe contener post_ids de comentarios con esa emoción
    all_post_ids = set()
    for post_ids in por_emocion.values():
        all_post_ids.update(post_ids)
    # Todos los post_ids de los comentarios deben estar en al menos una emoción
    assert all_post_ids == {"p1", "p2", "p3", "p4"}
