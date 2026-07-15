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
    data = construir_analysis(_sample_aprobaciones(), "2026-04", "2026-04-30")
    voces = data["bloque2"]["voces_influencia"]
    assert len(voces) == 3


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
