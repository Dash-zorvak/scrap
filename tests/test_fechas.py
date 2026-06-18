"""Tests para resolver_fecha_relativa (deuda técnica #1: fechas relativas).

Fecha de referencia fija para determinismo: 2026-06-18.
"""
from datetime import date, datetime

from dashboard.ingreso_extraccion import resolver_fecha_relativa, _fecha_confianza

HOY = date(2026, 6, 18)


class TestResolverFechaRelativa:
    def test_iso_passthrough(self):
        assert resolver_fecha_relativa("2026-05-01", HOY) == "2026-05-01"

    def test_iso_datetime_passthrough(self):
        assert resolver_fecha_relativa("2026-05-01T10:30:00", HOY) == "2026-05-01"

    def test_horas(self):
        assert resolver_fecha_relativa("hace 2 h", HOY) == "2026-06-18"

    def test_horas_4(self):
        assert resolver_fecha_relativa("hace 4 h", HOY) == "2026-06-18"

    def test_horas_sin_hace(self):
        assert resolver_fecha_relativa("2 h", HOY) == "2026-06-18"

    def test_minutos(self):
        assert resolver_fecha_relativa("hace 35 min", HOY) == "2026-06-18"

    def test_segundos(self):
        assert resolver_fecha_relativa("hace 10 s", HOY) == "2026-06-18"

    def test_ayer(self):
        assert resolver_fecha_relativa("ayer", HOY) == "2026-06-17"

    def test_hoy(self):
        assert resolver_fecha_relativa("hoy", HOY) == "2026-06-18"

    def test_anteayer(self):
        assert resolver_fecha_relativa("anteayer", HOY) == "2026-06-16"

    def test_dias(self):
        assert resolver_fecha_relativa("hace 3 días", HOY) == "2026-06-15"

    def test_dias_abrev(self):
        assert resolver_fecha_relativa("hace 3 d", HOY) == "2026-06-15"

    def test_semanas(self):
        assert resolver_fecha_relativa("hace 2 semanas", HOY) == "2026-06-04"

    def test_semana_abrev(self):
        assert resolver_fecha_relativa("hace 1 sem", HOY) == "2026-06-11"

    def test_meses(self):
        assert resolver_fecha_relativa("hace 2 meses", HOY) == "2026-04-19"

    def test_anio(self):
        assert resolver_fecha_relativa("hace 1 año", HOY) == "2025-06-18"

    def test_nombre_mes(self):
        assert resolver_fecha_relativa("17 de junio", HOY) == "2026-06-17"

    def test_nombre_mes_con_anio(self):
        assert resolver_fecha_relativa("5 de enero de 2025", HOY) == "2025-01-05"

    def test_nombre_mes_futuro_usa_anio_anterior(self):
        assert resolver_fecha_relativa("20 de diciembre", HOY) == "2025-12-20"

    def test_datetime_hoy(self):
        assert resolver_fecha_relativa("hace 2 h", datetime(2026, 6, 18, 9, 0)) == "2026-06-18"

    def test_none(self):
        assert resolver_fecha_relativa(None, HOY) is None

    def test_vacio(self):
        assert resolver_fecha_relativa("", HOY) is None

    def test_basura(self):
        assert resolver_fecha_relativa("publicado", HOY) is None


class TestFechaConfianzaConResolucion:
    def test_relativa_se_resuelve_y_degrada_a_dudoso(self):
        r = _fecha_confianza({"valor": "hace 2 h", "confianza": "seguro"}, hoy=HOY)
        assert r == {"valor": "2026-06-18", "confianza": "dudoso"}

    def test_iso_se_conserva_seguro(self):
        r = _fecha_confianza({"valor": "2026-05-01", "confianza": "seguro"}, hoy=HOY)
        assert r == {"valor": "2026-05-01", "confianza": "seguro"}

    def test_no_interpretable_es_no_detectado(self):
        r = _fecha_confianza({"valor": "publicado", "confianza": "seguro"}, hoy=HOY)
        assert r == {"valor": None, "confianza": "no_detectado"}

    def test_none_es_no_detectado(self):
        r = _fecha_confianza(None, hoy=HOY)
        assert r == {"valor": None, "confianza": "no_detectado"}
