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
