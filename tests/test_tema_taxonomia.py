from dashboard.tema_taxonomia import (
    CATEGORIAS_VALIDAS,
    TEMAS_VISIBLES,
    remapear,
    etiqueta_tema,
)


class TestTaxonomia:
    def test_categorias_englobantes(self):
        esperadas = {
            "obras_servicios", "seguridad", "movilidad", "empleo", "salud",
            "educacion", "medio_ambiente", "gobernanza", "cultura_deportes",
            "apoyo_generico", "no_aplica",
        }
        assert CATEGORIAS_VALIDAS == esperadas

    def test_no_quedan_claves_viejas(self):
        for vieja in ("obras_publicas", "servicios_publicos", "corrupcion",
                      "transparencia", "cultura", "deportes"):
            assert vieja not in CATEGORIAS_VALIDAS

    def test_no_aplica_no_es_visible(self):
        assert "no_aplica" in CATEGORIAS_VALIDAS
        assert "no_aplica" not in TEMAS_VISIBLES


class TestRemapear:
    def test_fusiones(self):
        assert remapear("obras_publicas") == "obras_servicios"
        assert remapear("servicios_publicos") == "obras_servicios"
        assert remapear("corrupcion") == "gobernanza"
        assert remapear("transparencia") == "gobernanza"
        assert remapear("cultura") == "cultura_deportes"
        assert remapear("deportes") == "cultura_deportes"

    def test_identidad(self):
        assert remapear("seguridad") == "seguridad"
        assert remapear("salud") == "salud"
        assert remapear("educacion") == "educacion"

    def test_vacio_y_desconocido(self):
        assert remapear("") == ""
        assert remapear(None) == ""
        assert remapear("inexistente") == "no_aplica"


class TestEtiqueta:
    def test_etiqueta_directa(self):
        assert etiqueta_tema("gobernanza") == "Transparencia y confianza"
        assert etiqueta_tema("obras_servicios") == "Obras y servicios públicos"

    def test_etiqueta_via_remap(self):
        assert etiqueta_tema("corrupcion") == "Transparencia y confianza"
        assert etiqueta_tema("deportes") == "Cultura y deportes"
