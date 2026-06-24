"""Tests del Bloque I (calculos puros de pulso general)."""

import pandas as pd

from dashboard.dash_pulso import (
    calcular_clima_diario,
    calcular_intensidad_vs_promedio,
    calcular_concentracion,
)


class TestClimaDiario:
    def test_tono_y_tendencia(self):
        df = pd.DataFrame({
            "pct_positivo": [50, 70],
            "pct_negativo": [30, 10],
            "total_comentarios": [10, 10],
            "created_time": ["2026-01-01", "2026-01-02"],
        })
        r = calcular_clima_diario(df)
        assert r is not None
        assert r["fecha"] == "2026-01-02"
        assert r["pct_favorable"] == 70.0
        assert r["pct_adverso"] == 10.0
        assert r["pct_neutro"] == 20.0
        assert r["delta_favorable"] == 20.0

    def test_un_solo_dia_sin_delta(self):
        df = pd.DataFrame({
            "pct_positivo": [60],
            "pct_negativo": [20],
            "total_comentarios": [5],
            "created_time": ["2026-01-01"],
        })
        r = calcular_clima_diario(df)
        assert r is not None
        assert r["delta_favorable"] is None

    def test_vacio(self):
        assert calcular_clima_diario(pd.DataFrame()) is None
        assert calcular_clima_diario(None) is None


class TestIntensidad:
    def test_hoy_vs_promedio(self):
        df_fb = pd.DataFrame({
            "created_time": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "engagement_total": [100, 100, 200],
        })
        r = calcular_intensidad_vs_promedio(df_fb, None)
        assert r is not None
        assert r["vol_hoy"] == 200.0
        assert r["promedio"] == 100.0
        assert round(r["pct_dif"]) == 100
        assert r["n_ref"] == 2

    def test_un_solo_dia_devuelve_none(self):
        df_fb = pd.DataFrame({
            "created_time": ["2026-01-01"],
            "engagement_total": [100],
        })
        assert calcular_intensidad_vs_promedio(df_fb, None) is None

    def test_vacio(self):
        assert calcular_intensidad_vs_promedio(None, None) is None


class TestConcentracion:
    def test_dominado(self):
        r = calcular_concentracion({"A": 60, "B": 20, "C": 20})
        assert r["nivel"] == "dominado"
        assert r["share_top"] == 60.0
        assert r["share_resto"] == 40.0
        assert r["n_temas"] == 3

    def test_liderado(self):
        r = calcular_concentracion({"A": 40, "B": 30, "C": 30})
        assert r["nivel"] == "liderado"

    def test_fragmentado(self):
        r = calcular_concentracion({"A": 20, "B": 20, "C": 20, "D": 20, "E": 20})
        assert r["nivel"] == "fragmentado"

    def test_vacio(self):
        assert calcular_concentracion({}) is None
        assert calcular_concentracion(None) is None
