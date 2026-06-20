import pytest
from src.analyzer.zone_tagger import (
    _normalizar,
    detectar_zona,
    taggear_serie,
)


class TestNormalizar:
    def test_lower(self):
        assert _normalizar("CaNtOn NaTiViDaD") == "canton natividad"

    def test_quitar_tildes(self):
        assert _normalizar("cándelária") == "candelaria"

    def test_colapsar_espacios(self):
        assert _normalizar("canton   natividad") == "canton natividad"

    def test_run_on_split(self):
        assert _normalizar("lapanades") == "la panades"

    def test_vacio(self):
        assert _normalizar("") == ""
        assert _normalizar(None) == ""

    def test_trailing_spaces(self):
        assert _normalizar("  canton natividad  ") == "canton natividad"


class TestDetectarZona:
    def test_canton_y_caserio(self):
        r = detectar_zona("aqui en el canton natividad caserio cruz verde estamos botados")
        assert r["zona"] == "caserio cruz verde"
        assert r["zona_tipo"] == "caserio"
        assert r["match"] == "caserio cruz verde"

    def test_caserio_priority(self):
        r = detectar_zona("caserio cruz verde canton natividad")
        assert r["zona_tipo"] == "caserio"

    def test_calle_detras_terminal(self):
        r = detectar_zona("la calle detras de la terminal es un desastre")
        assert r["entidad"] is not None
        assert "calle" in r["entidad"]
        assert "terminal" in r["entidad"] or "detras" in r["entidad"]
        assert r["zona_tipo"] in ("lugar_emblematico", "entidad")

    def test_run_on_tolerance(self):
        r = detectar_zona("Lapanades nos dejaron en los barrancos")
        assert r["zona"] is not None
        assert "panades" in r["zona"] or "la panades" in r["zona"]

    def test_sin_zona(self):
        r = detectar_zona("todo excelente alcalde")
        assert r["zona"] is None
        assert r["zona_tipo"] is None
        assert r["entidad"] is None
        assert r["match"] is None

    def test_vacio_y_none(self):
        r1 = detectar_zona("")
        assert r1["zona"] is None
        r2 = detectar_zona(None)
        assert r2["zona"] is None

    def test_mayusculas(self):
        r = detectar_zona("VIVIMOS EN EL CANTON NATIVIDAD")
        assert r["zona"] == "canton natividad"

    def test_sin_tilde_tolerancia(self):
        r = detectar_zona("canton natividad sin agua")
        assert r["zona"] == "canton natividad"

    def test_entidad_calle(self):
        r = detectar_zona("la calle libertad esta en mal estado")
        assert r["entidad"] is not None
        assert "calle" in r["entidad"]

    def test_entidad_avenida(self):
        r = detectar_zona("avenida independencia necesita reparacion")
        assert r["entidad"] is not None
        assert "avenida" in r["entidad"]

    def test_colonia_match(self):
        r = detectar_zona("en la colonia belen no hay alumbrado")
        assert r["zona"] is not None
        assert r["zona_tipo"] == "colonia"

    def test_municipio_match(self):
        r = detectar_zona("chalchuapa necesita mas atencion")
        assert r["zona"] is not None
        assert r["zona_tipo"] == "municipio"

    def test_canton_prioridad_sobre_colonia(self):
        r = detectar_zona("canton natividad colonia belen")
        assert r["zona_tipo"] == "canton"

    def test_lugar_emblematico_prioridad(self):
        r = detectar_zona("parque libertad en el canton natividad")
        assert r["zona_tipo"] == "lugar_emblematico"

    def test_terminal_detras(self):
        r = detectar_zona("detras de la terminal hay problemas")
        assert r["zona"] is not None
        assert r["zona_tipo"] in ("lugar_emblematico", "entidad")

    def test_el_puente(self):
        r = detectar_zona("el puente esta en mal estado")
        assert r["zona"] is not None


class TestTaggearSerie:
    def test_lista_vacia(self):
        assert taggear_serie([]) == []

    def test_lista_textos(self):
        textos = [
            "aqui en el canton natividad",
            "todo excelente",
        ]
        resultados = taggear_serie(textos)
        assert len(resultados) == 2
        assert resultados[0]["zona"] == "canton natividad"
        assert resultados[1]["zona"] is None

    def test_none_en_lista(self):
        resultados = taggear_serie([None, "canton natividad"])
        assert resultados[0]["zona"] is None
        assert resultados[1]["zona"] == "canton natividad"
