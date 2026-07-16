"""Tests para tema_taxonomia.py — catálogo de emociones expandido (Puntos 3.4, 3.5)."""
import pytest

from dashboard.tema_taxonomia import (
    EMOCIONES,
    EMOCIONES_VALIDAS,
    EMOCION_LABELS,
    normalizar_emocion,
    familia_de,
    emociones_por_familia,
)


class TestCatalogoExpandido:
    def test_total_emociones_mayor_45(self):
        assert len(EMOCIONES) >= 45, f"Se esperaban >=45 emociones, hay {len(EMOCIONES)}"

    def test_no_slash_en_familias_principales(self):
        familias_primarias = {
            "joy", "trust", "fear", "surprise", "sadness",
            "disgust", "anger", "anticipation",
        }
        for clave, meta in EMOCIONES.items():
            if meta["familia"] in familias_primarias:
                assert "/" not in meta["label"], (
                    f"{clave} tiene '/' en label '{meta['label']}' "
                    f"en familia primaria '{meta['familia']}'"
                )

    def test_slash_permitido_en_diadas(self):
        """Las díadas pueden tener labels duales (son conceptos combinados)."""
        for clave, meta in EMOCIONES.items():
            if meta["familia"] == "diada":
                # No debería tener slash en familias primarias, pero diadas OK
                pass


class TestEmocionesNuevas:
    def test_panico_existe(self):
        assert "panico" in EMOCIONES_VALIDAS
        assert EMOCIONES["panico"]["familia"] == "fear"
        assert EMOCIONES["panico"]["intensidad"] == "intensa"

    def test_pena_profunda_existe(self):
        assert "pena_profunda" in EMOCIONES_VALIDAS
        assert EMOCIONES["pena_profunda"]["familia"] == "sadness"

    def test_indignacion_moral_existe(self):
        assert "indignacion_moral" in EMOCIONES_VALIDAS
        assert EMOCIONES["indignacion_moral"]["familia"] == "disgust"

    def test_indiferencia_existe(self):
        assert "indiferencia" in EMOCIONES_VALIDAS
        assert EMOCIONES["indiferencia"]["familia"] == "disgust"

    def test_molestia_existe(self):
        assert "molestia" in EMOCIONES_VALIDAS
        assert EMOCIONES["molestia"]["familia"] == "anger"

    def test_ira_existe(self):
        assert "ira" in EMOCIONES_VALIDAS
        assert EMOCIONES["ira"]["familia"] == "anger"

    def test_alerta_expectante_existe(self):
        assert "alerta_expectante" in EMOCIONES_VALIDAS
        assert EMOCIONES["alerta_expectante"]["familia"] == "anticipation"


class TestNuevasDiadas:
    @pytest.mark.parametrize("clave", [
        "envidia", "culpa", "curiosidad", "esperanza",
        "indignacion", "incredulidad", "ansiedad", "pesimismo",
    ])
    def test_diada_existe(self, clave):
        assert clave in EMOCIONES_VALIDAS
        assert EMOCIONES[clave]["familia"] == "diada"
        assert "deriva_de" in EMOCIONES[clave]

    def test_diadas_totales_16(self):
        diadas = [k for k, v in EMOCIONES.items() if v["familia"] == "diada"]
        assert len(diadas) == 16


class TestCivicaIntensidad:
    @pytest.mark.parametrize("clave", [
        "reclamo", "objecion", "satisfaccion", "calma",
        "reconocimiento", "ironia",
    ])
    def test_civica_tiene_intensidad(self, clave):
        assert "intensidad" in EMOCIONES[clave], (
            f"{clave} no tiene campo 'intensidad'"
        )


class TestNormalizarEmocion:
    def test_normalizar_nueva_emocion(self):
        assert normalizar_emocion("panico") == "panico"

    def test_normalizar_panic_sinonimo(self):
        assert normalizar_emocion("pánico") == "panico"

    def test_normalizar_ira(self):
        assert normalizar_emocion("ira") == "ira"

    def test_normalizar_iracundo_mapea_a_ira(self):
        assert normalizar_emocion("iracundo") == "ira"

    def test_normalizar_indignacion_moral(self):
        assert normalizar_emocion("indignación moral") == "indignacion_moral"

    def test_normalizar_envidia(self):
        assert normalizar_emocion("envidioso") == "envidia"

    def test_normalizar_esperanza(self):
        assert normalizar_emocion("ojalá") == "esperanza"

    def test_normalizar_invalid_lanza_value_error(self):
        with pytest.raises(ValueError, match="no reconocida"):
            normalizar_emocion("emocion_fantasma_xyz")


class TestFamiliaDe:
    def test_familia_terror(self):
        assert familia_de("terror") == "fear"

    def test_familia_panico(self):
        assert familia_de("panico") == "fear"

    def test_familia_envidia(self):
        assert familia_de("envidia") == "diada"

    def test_familia_desconocida_default(self):
        assert familia_de("no_existe") == "civica"


class TestEmocionesPorFamilia:
    def test_todas_las_familias_presentes(self):
        resultado = emociones_por_familia()
        for fam in ["joy", "trust", "fear", "surprise", "sadness",
                     "disgust", "anger", "anticipation", "diada", "civica"]:
            assert fam in resultado, f"Familia '{fam}' no encontrada"

    def test_fear_tiene_4(self):
        resultado = emociones_por_familia()
        assert len(resultado["fear"]) == 4

    def test_diada_tiene_16(self):
        resultado = emociones_por_familia()
        assert len(resultado["diada"]) == 16
