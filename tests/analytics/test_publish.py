"""Tests para analytics/publish.py (T4.4)."""
import json
import os
import tempfile
import shutil
import pytest
from analytics.publish import publicar_analysis, _crear_backup


@pytest.fixture
def tmp_analysis(tmp_path):
    """Crea un data/ y devuelve la ruta a analysis.json."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir / "analysis.json"


def _base_valid():
    return {
        "meta": {"periodo": "2026-04", "fecha_datos_hasta": "2026-04-30", "generado_en": "t"},
        "bloque1": {
            "clima_narrativo": {"narrativa": "", "enlaces_referencia": []},
            "indice_emociones": {"emocion_dominante": "calma", "narrativa": "", "enlaces_referencia": []},
            "intensidad": {"narrativa": "", "enlaces_referencia": []},
            "concentracion_tematica": {
                "ramas": [{"tema": "seguridad", "share": 50.0, "emocion_dominante": "calma"},
                          {"tema": "movilidad", "share": 50.0, "emocion_dominante": "calma"}],
                "narrativa": "", "enlaces_referencia": [],
            },
            "pulso_iq": {"narrativa": "", "enlaces_referencia": []},
            "metricas_rendimiento": {"narrativa": "", "enlaces_referencia": []},
        },
        "bloque2": {"voces_influencia": []},
        "bloque3": {
            "puntos_friccion": [],
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


def test_publicar_escribe_archivo(tmp_analysis):
    datos = _base_valid()
    r = publicar_analysis(datos, path=str(tmp_analysis))
    assert r.es_publicable
    assert tmp_analysis.exists()
    with open(tmp_analysis) as f:
        leido = json.load(f)
    assert leido["meta"]["periodo"] == "2026-04"


def test_publicar_falla_con_datos_invalidos(tmp_analysis):
    datos = {"meta": {}, "bloque1": {}, "bloque2": {}, "bloque3": {}, "bloque4": {}}
    r = publicar_analysis(datos, path=str(tmp_analysis))
    assert not r.es_publicable
    assert not tmp_analysis.exists()


def test_backup_se_crea(tmp_analysis):
    datos = _base_valid()
    publicar_analysis(datos, path=str(tmp_analysis))
    # Escribir de nuevo para que cree backup
    datos["meta"]["periodo"] = "2026-05"
    publicar_analysis(datos, path=str(tmp_analysis))
    backup_dir = tmp_analysis.parent / "_analysis_backups"
    assert backup_dir.exists()
    backups = [f for f in os.listdir(backup_dir) if f.startswith("analysis.json")]
    assert len(backups) == 1


def test_backup_limpia_los_antiguos(tmp_analysis):
    datos = _base_valid()
    for i in range(8):
        datos["meta"]["periodo"] = f"2026-{i+1:02d}"
        publicar_analysis(datos, path=str(tmp_analysis), max_backups=3)
    backup_dir = tmp_analysis.parent / "_analysis_backups"
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("analysis.json")])
    assert len(backups) == 3


def test_archivo_es_atomico(tmp_analysis):
    datos = _base_valid()
    publicar_analysis(datos, path=str(tmp_analysis))
    # Verificar que no quedaron archivos temporales
    dir_contents = os.listdir(tmp_analysis.parent)
    tmp_files = [f for f in dir_contents if f.startswith(".analysis_")]
    assert len(tmp_files) == 0
