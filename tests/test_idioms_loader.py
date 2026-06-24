"""Tests de la Capa 3 (ampliacion): carga de dichos desde idioms_sv_global.json.

Verifica que el loader:
  - extrae frases idiomaticas multi-palabra de las secciones esperadas;
  - excluye palabras sueltas (caliche / exclamaciones de una palabra);
  - deduplica y recorta signos de los bordes;
  - es defensivo ante archivos ausentes o malformados;
y que la integracion con topic_detection:
  - amplia DICHOS_LOCALES sin perder la lista base;
  - no rompe la asignacion de tema por una sola palabra fuerte;
  - bloquea como tema un modismo del JSON que contiene una palabra clave.
"""
import json

import pytest

from src.analyzer.idioms_loader import cargar_idioms_raw, extraer_dichos


SAMPLE = {
    "salvadoreno": {
        "dichos_idiomaticos": {
            "entradas": [
                {"expresion": "Hablar paja", "significado_real": "x"},
                {"expresion": "Vaya pues", "significado_real": "x"},
                {"expresion": "Joderse", "significado_real": "x"},
            ]
        },
        "refranes": {
            "entradas": [
                {"refran": "Al que madruga, Dios le ayuda", "valence": "positivo"},
            ]
        },
        "caliche_palabras": {
            "entradas": [
                {"palabra": "chivo", "significado_real": "bueno"},
            ]
        },
    },
    "global_espanol": {
        "modismos_universales": {
            "entradas": [
                {"expresion": "Meter la pata", "valence_real": "negativo"},
            ]
        },
        "modismos_latinoamerica": {
            "entradas": [
                {"expresion": "\u00a1\u00d3rale!", "significado_real": "ok"},
                {"expresion": "\u00bfQu\u00e9 m\u00e1s pues?", "significado_real": "saludo"},
            ]
        },
        "expresiones_redes_sociales": {
            "entradas": [
                {"expresion": "Se pas\u00f3", "significado_real": "ambiguo"},
            ]
        },
    },
}


class TestExtraerDichos:
    def test_incluye_frases_multipalabra(self):
        bajos = [d.lower() for d in extraer_dichos(SAMPLE)]
        assert "hablar paja" in bajos
        assert "vaya pues" in bajos
        assert "al que madruga, dios le ayuda" in bajos
        assert "meter la pata" in bajos
        assert "qu\u00e9 m\u00e1s pues" in bajos

    def test_excluye_palabras_sueltas(self):
        bajos = [d.lower() for d in extraer_dichos(SAMPLE)]
        assert "joderse" not in bajos
        assert "\u00f3rale" not in bajos
        assert "orale" not in bajos

    def test_ignora_caliche_y_redes(self):
        bajos = [d.lower() for d in extraer_dichos(SAMPLE)]
        assert "chivo" not in bajos
        assert "se pas\u00f3" not in bajos
        assert "se paso" not in bajos

    def test_recorta_signos_de_borde(self):
        dichos = extraer_dichos(SAMPLE)
        unidos = "".join(dichos)
        assert "\u00bf" not in unidos
        assert "\u00a1" not in unidos
        assert not any(d.endswith("?") for d in dichos)

    def test_dedup(self):
        data = {
            "salvadoreno": {
                "dichos_idiomaticos": {
                    "entradas": [
                        {"expresion": "Hablar paja"},
                        {"expresion": "hablar paja"},
                    ]
                }
            }
        }
        assert len(extraer_dichos(data)) == 1

    def test_min_palabras_configurable(self):
        bajos = [d.lower() for d in extraer_dichos(SAMPLE, min_palabras=3)]
        assert "hablar paja" not in bajos
        assert "meter la pata" in bajos


class TestDefensivo:
    def test_archivo_inexistente(self):
        assert cargar_idioms_raw("/ruta/que/no/existe/idioms.json") == {}

    def test_extraer_data_vacia(self):
        assert extraer_dichos({}) == []

    def test_extraer_secciones_faltantes(self):
        assert extraer_dichos({"salvadoreno": {}}) == []

    def test_entradas_no_lista(self):
        data = {"salvadoreno": {"dichos_idiomaticos": {"entradas": "no-es-lista"}}}
        assert extraer_dichos(data) == []

    def test_json_malformado(self, tmp_path):
        ruta = tmp_path / "malo.json"
        ruta.write_text("{ esto no es json", encoding="utf-8")
        assert cargar_idioms_raw(ruta) == {}

    def test_archivo_valido_via_env(self, tmp_path, monkeypatch):
        ruta = tmp_path / "idioms.json"
        ruta.write_text(json.dumps(SAMPLE), encoding="utf-8")
        monkeypatch.setenv("IDIOMS_SV_PATH", str(ruta))
        bajos = [d.lower() for d in extraer_dichos()]
        assert "meter la pata" in bajos


class TestArchivoRealDelRepo:
    def test_carga_desde_raiz_repo(self):
        dichos = extraer_dichos()
        assert isinstance(dichos, list)
        assert len(dichos) > 0
        assert all(len(d.split()) >= 2 for d in dichos)
        bajos = [d.lower() for d in dichos]
        assert "meter la pata" in bajos


class TestIntegracionTopicDetection:
    def test_dichos_locales_incluye_base_y_json(self):
        from src.analyzer.topic_detection import DICHOS_LOCALES
        bajos = [d.lower() for d in DICHOS_LOCALES]
        assert "panchito el rio estaba" in bajos
        assert "meter la pata" in bajos

    def test_palabra_fuerte_sola_sigue_asignando(self):
        from src.analyzer.topic_detection import get_main_topic
        assert get_main_topic("nuevas oportunidades de empleo") == "empleo"

    def test_dicho_del_json_bloquea_tema(self):
        from src.analyzer.topic_detection import get_main_topic, detect_topics
        # \"matar dos pajaros de un tiro\": sin Capa 3, \"matar\" daria seguridad;
        # como es un modismo del JSON, no debe asignar ningun tema.
        assert get_main_topic("matar dos p\u00e1jaros de un tiro") == ""
        assert detect_topics("matar dos p\u00e1jaros de un tiro") == []
