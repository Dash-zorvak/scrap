"""Tests para entidades_taxonomia.py — catálogo de entidades (Punto 1)."""
import pytest

from dashboard.entidades_taxonomia import (
    ENTIDADES,
    ENTIDADES_VALIDAS,
    ENTIDAD_LABELS,
    etiqueta_entidad,
    tema_de_entidad,
)


class TestEntidades:
    def test_catalogo_no_vacio(self):
        assert len(ENTIDADES) >= 5

    def test_etiquetas_no_vacias(self):
        for clave, meta in ENTIDADES.items():
            assert "label" in meta and meta["label"]
            assert "tema_englobante" in meta

    def test_etiqueta_entidad_clave_conocida(self):
        assert etiqueta_entidad("alcaldia") == "La Alcaldía"

    def test_etiqueta_entidad_vacia(self):
        assert "Sin entidad" in etiqueta_entidad("")

    def test_etiqueta_entidad_desconocida(self):
        resultado = etiqueta_entidad("xyz_no_existe")
        assert "xyz no existe" in resultado.lower()

    def test_tema_de_entidad(self):
        assert tema_de_entidad("alcaldia") == "gobernanza"

    def test_tema_de_entidad_desconocida(self):
        assert tema_de_entidad("no_existe") == ""

    def test_entidades_validas_es_set(self):
        assert isinstance(ENTIDADES_VALIDAS, set)
        assert len(ENTIDADES_VALIDAS) >= 5
