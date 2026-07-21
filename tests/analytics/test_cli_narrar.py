"""Tests para analytics/cli.py - comando narrar."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock

from analytics.cli import _construir_contexto_seccion, _construir_contexto_seccion_b4


def _analysis_base():
    """analysis.json minimo para tests de narrar."""
    return {
        "meta": {
            "periodo": "2026-04",
            "fecha_datos_hasta": "2026-04-30",
            "generado_en": "2026-05-01T10:00:00",
        },
        "bloque1": {
            "clima_narrativo": {
                "tono_dominante": "positivo",
                "pct_favorable": 45.0,
                "pct_neutral": 30.0,
                "pct_critico": 25.0,
                "n_total_comentarios": 200,
                "tono_score_hoy": 20.0,
                "tono_score_ayer": 0.0,
                "tendencia": 20.0,
                "etiqueta_tendencia": "mejorando",
                "narrativa": "",
                "enlaces_referencia": [],
                "formula_usada": "NSI = ...",
            },
            "indice_emociones": {
                "emocion_dominante": "calma",
                "narrativa": "",
                "enlaces_referencia": [],
                "pct_calma": 50.0,
            },
            "intensidad": {
                "vol_hoy": 200,
                "promedio_semanal": 200,
                "pct_diferencia": 0.0,
                "narrativa": "",
                "enlaces_referencia": [],
            },
            "concentracion_tematica": {
                "ramas": [{"tema": "seguridad", "share": 50.0, "emocion_dominante": "calma"}],
                "hhi": 0.5,
                "nivel": "dominado",
                "top_tema": "seguridad",
                "n_temas": 1,
                "narrativa": "",
                "enlaces_referencia": [],
            },
            "pulso_iq": {"valor": 0.7, "cuadrante": "estable", "narrativa": "", "enlaces_referencia": []},
            "metricas_rendimiento": {
                "engagement_rate": 3.5,
                "narrativa": "",
                "enlaces_referencia": [],
            },
        },
        "bloque2": {
            "voces_influencia": [
                {
                    "pagina": "Alcaldia",
                    "engagement": 1500,
                    "reacciones_totales": 1000,
                    "comentarios_totales": 300,
                    "compartidos_totales": 200,
                    "narrativa": "",
                    "enlaces_referencia": [],
                },
            ],
            "polarizacion": {
                "indice": 0.3,
                "nivel": "dividida",
                "narrativa": "",
                "enlaces_referencia": [],
            },
        },
        "bloque3": {
            "puntos_friccion": [
                {
                    "tema": "seguridad",
                    "n_negativos": 45,
                    "n_comentarios_total": 100,
                    "pct_del_total": 22.5,
                    "emocion_dominante": "enojo",
                    "citas_moderadas": [],
                    "narrativa": "",
                    "enlaces_relacionados": [],
                },
            ],
            "autenticidad": {"pct_organico": 95.0, "pct_coordinado": 5.0, "narrativa": "", "enlaces_referencia": []},
            "velocidad_propagacion": {"proyeccion_24h": "", "narrativa": "", "enlaces_referencia": []},
            "nivel_alerta": {
                "semaforo": "verde",
                "indice_riesgo": 15.0,
                "alertas_cambridge": [],
                "narrativa": "",
                "enlaces_referencia": [],
            },
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


def test_construir_contexto_seccion_extrae_campos_numericos():
    """Extrae solo campos numericos/categoricos, excluye narrativa/enlaces."""
    sec = {
        "narrativa": "texto largo",
        "enlaces_referencia": ["https://a.com"],
        "pct_favorable": 45.0,
        "tono_dominante": "positivo",
        "formula_usada": "NSI = ...",
    }
    ctx = _construir_contexto_seccion(sec)
    assert "pct_favorable" in ctx
    assert "tono_dominante" in ctx
    assert "narrativa" not in ctx
    assert "enlaces_referencia" not in ctx
    assert "formula_usada" not in ctx


def test_construir_contexto_seccion_b4_incluye_datos_bloques():
    """Contexto de bloque4 incluye datos relevantes de bloque1 y bloque3."""
    data = _analysis_base()
    ctx = _construir_contexto_seccion_b4(data, "eco_historico")
    assert ctx["periodo"] == "2026-04"
    assert ctx["seccion"] == "eco_historico"
    assert ctx["tono_dominante"] == "positivo"
    assert ctx["pct_favorable"] == 45.0
    assert ctx["emocion_dominante"] == "calma"
    assert ctx["semaforo"] == "verde"


def test_narrar_no_modifica_campos_calculados(monkeypatch, tmp_path):
    """narrar no modifica ningun campo numerico/calculado de analysis.json."""
    data = _analysis_base()
    data_path = tmp_path / "analysis.json"
    with open(data_path, "w") as f:
        json.dump(data, f)

    # Guardar valores originales
    orig_pct = data["bloque1"]["clima_narrativo"]["pct_favorable"]
    orig_eng = data["bloque2"]["voces_influencia"][0]["engagement"]
    orig_fric = data["bloque3"]["puntos_friccion"][0]["n_negativos"]

    # Mock Claude para que devuelva algo
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Narrativa de prueba.")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("analytics.narrator_claude.Anthropic", return_value=mock_client):
        args = MagicMock()
        args.path = str(data_path)
        args.dry_run = False

        from analytics.cli import cmd_narrar
        with patch("analytics.publish.publicar_analysis") as mock_pub:
            mock_pub.return_value = MagicMock(es_publicable=True, advertencias=lambda: [])
            cmd_narrar(args)

    # Verificar que campos calculados NO cambiaron
    assert data["bloque1"]["clima_narrativo"]["pct_favorable"] == orig_pct
    assert data["bloque2"]["voces_influencia"][0]["engagement"] == orig_eng
    assert data["bloque3"]["puntos_friccion"][0]["n_negativos"] == orig_fric


def test_narrar_dry_run_no_escribe(monkeypatch, tmp_path):
    """--dry-run imprime narrativas sin escribir el archivo."""
    data = _analysis_base()
    data_path = tmp_path / "analysis.json"
    with open(data_path, "w") as f:
        json.dump(data, f)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Narrativa dry run.")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("analytics.narrator_claude.Anthropic", return_value=mock_client):
        args = MagicMock()
        args.path = str(data_path)
        args.dry_run = True

        from analytics.cli import cmd_narrar
        result = cmd_narrar(args)

    assert result == 0
    # Verificar que el archivo no fue modificado
    with open(data_path) as f:
        data_after = json.load(f)
    assert data_after["bloque1"]["clima_narrativo"]["narrativa"] == ""


def test_narrar_fallo_parcial_no_tumba_ejecucion(monkeypatch, tmp_path):
    """Si Claude falla en una seccion, el resto se publica igual."""
    data = _analysis_base()
    data_path = tmp_path / "analysis.json"
    with open(data_path, "w") as f:
        json.dump(data, f)

    call_count = [0]
    def fake_redactar(system_prompt, contexto, max_tokens=None, section_code=""):
        call_count[0] += 1
        if "b1.clima_narrativo" in section_code:
            raise Exception("Claude timeout")
        return f"Narrativa generada para {section_code}"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("analytics.narrator_claude.redactar_narrativa", side_effect=fake_redactar):
        args = MagicMock()
        args.path = str(data_path)
        args.dry_run = False

        from analytics.cli import cmd_narrar
        with patch("analytics.publish.publicar_analysis") as mock_pub:
            mock_pub.return_value = MagicMock(es_publicable=True, advertencias=lambda: [])
            result = cmd_narrar(args)

    assert result == 0
    # Verificar que se intento narrar todas las secciones
    assert call_count[0] > 1


def test_narrar_archivo_no_existe(monkeypatch, tmp_path):
    """Si analysis.json no existe, retorna error."""
    args = MagicMock()
    args.path = str(tmp_path / "no_existe.json")

    from analytics.cli import cmd_narrar
    result = cmd_narrar(args)
    assert result == 1
