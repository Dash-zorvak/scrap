"""Tests del Bloque IV — evolución temática y comparativa sectorial."""

from dashboard.dash_memoria import (
    clasificar_evolucion_temas,
    comparar_sectorial,
)


class TestEvolucionTemas:
    def test_emergente(self):
        r = clasificar_evolucion_temas({"Baches": 5}, {})
        assert [i["tema"] for i in r["emergentes"]] == ["Baches"]
        assert r["emergentes"][0]["n_actual"] == 5

    def test_extincion(self):
        r = clasificar_evolucion_temas({}, {"Fiestas": 4})
        assert [i["tema"] for i in r["en_extincion"]] == ["Fiestas"]

    def test_declive(self):
        # cae de 10 a 4 => -60% => en declive
        r = clasificar_evolucion_temas({"Agua": 4}, {"Agua": 10})
        assert [i["tema"] for i in r["en_declive"]] == ["Agua"]
        assert r["en_declive"][0]["cambio_pct"] == -60.0

    def test_auge(self):
        # sube de 4 a 10 => +150% => en auge
        r = clasificar_evolucion_temas({"Seguridad": 10}, {"Seguridad": 4})
        assert [i["tema"] for i in r["en_auge"]] == ["Seguridad"]

    def test_estable(self):
        # 10 -> 11 => +10% => estable
        r = clasificar_evolucion_temas({"Cultura": 11}, {"Cultura": 10})
        assert [i["tema"] for i in r["estables"]] == ["Cultura"]

    def test_orden_declive_mas_fuerte_primero(self):
        # A cae -50%, B cae -90% => B aparece primero
        r = clasificar_evolucion_temas({"A": 5, "B": 1}, {"A": 10, "B": 10})
        assert [i["tema"] for i in r["en_declive"]] == ["B", "A"]

    def test_vacio(self):
        r = clasificar_evolucion_temas({}, {})
        assert r == {
            "emergentes": [],
            "en_auge": [],
            "en_declive": [],
            "en_extincion": [],
            "estables": [],
        }


class TestComparativaSectorial:
    def test_sin_datos(self):
        assert comparar_sectorial(0.2, 0.1, 0, 0) is None
        assert comparar_sectorial(0.2, 0.1, 3, 0) is None

    def test_externo_mas_critico(self):
        r = comparar_sectorial(0.3, 0.0, 3, 50)
        assert r["brecha"] == -0.3
        assert "más negativo" in r["lectura"]
        assert r["tono_interno"] == "favorable"

    def test_externo_mas_positivo(self):
        r = comparar_sectorial(0.0, 0.3, 2, 20)
        assert "más positivo" in r["lectura"]

    def test_en_linea(self):
        r = comparar_sectorial(0.1, 0.1, 2, 10)
        assert "en línea" in r["lectura"]
