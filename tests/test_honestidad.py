"""Tests de la Capa 4 — honestidad en la clasificación de temas."""

from dashboard.dash_honestidad import resumen_honestidad


class TestResumenHonestidad:
    def test_sin_datos(self):
        assert resumen_honestidad(None) is None
        assert resumen_honestidad({}) is None
        assert resumen_honestidad({"total": 0}) is None

    def test_conteos_basicos(self):
        r = resumen_honestidad({
            "total": 100, "clasificados": 70, "no_aplica": 30,
            "dudosos": 10, "sarcasticos": 5, "por_reglas": 8,
            "umbral_dudoso": 0.55,
        })
        assert r["total"] == 100
        assert r["con_confianza"] == 60  # 70 - 10
        assert r["pct_con_confianza"] == 60.0
        assert r["no_aplica"] == 30
        assert r["pct_no_aplica"] == 30.0
        assert r["nivel_confiabilidad"] == "alta"

    def test_bar_suma_100(self):
        # con_confianza + dudosos + no_aplica deben cubrir el total exactamente,
        # porque clasificados + no_aplica == total.
        r = resumen_honestidad({
            "total": 100, "clasificados": 60, "no_aplica": 40, "dudosos": 15,
        })
        suma = r["pct_con_confianza"] + r["pct_dudosos"] + r["pct_no_aplica"]
        assert abs(suma - 100.0) < 0.01

    def test_nivel_media(self):
        # con_confianza = 50 - 10 = 40 => 40% => media
        r = resumen_honestidad({
            "total": 100, "clasificados": 50, "dudosos": 10, "no_aplica": 50,
        })
        assert r["con_confianza"] == 40
        assert r["nivel_confiabilidad"] == "media"

    def test_nivel_baja(self):
        # con_confianza = 20 - 5 = 15 => 15% => baja
        r = resumen_honestidad({
            "total": 100, "clasificados": 20, "dudosos": 5, "no_aplica": 80,
        })
        assert r["nivel_confiabilidad"] == "baja"

    def test_clamp_valores_inconsistentes(self):
        # dudosos > clasificados no debe producir negativos
        r = resumen_honestidad({
            "total": 10, "clasificados": 3, "dudosos": 50, "no_aplica": 7,
        })
        assert r["dudosos"] == 3
        assert r["con_confianza"] == 0
        assert r["pct_con_confianza"] == 0.0

    def test_lectura_menciona_cifras(self):
        r = resumen_honestidad({
            "total": 100, "clasificados": 70, "no_aplica": 30, "dudosos": 10,
            "por_reglas": 8,
        })
        assert "100" in r["lectura"]
        assert "%" in r["lectura"]
        assert "palabras clave" in r["lectura"]
