"""Tests de regresión para dash_bloque4 (Bloque IV — KPIs críticos)."""

import pandas as pd
import sys
import os

# Setup path like other dashboard tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from dashboard.dash_periodos import filtrar_por_fecha


class TestFiltrarPorFecha:
    """Regresión: filtrar_por_fecha existe y filtra correctamente por fecha."""

    def test_filtrar_por_fecha_basico(self):
        df = pd.DataFrame(
            {
                "created_time": pd.to_datetime(["2024-01-01", "2024-01-15", "2024-02-01"]),
                "valor": [1, 2, 3],
            }
        )
        ini = pd.Timestamp("2024-01-10")
        fin = pd.Timestamp("2024-01-20")
        res = filtrar_por_fecha(df, "created_time", ini, fin)
        assert len(res) == 1
        assert res.iloc[0]["valor"] == 2

    def test_filtrar_por_fecha_sin_columna(self):
        """Si la columna no existe, devuelve DataFrame vacío (no rompe)."""
        df = pd.DataFrame({"otra": [1, 2, 3]})
        res = filtrar_por_fecha(df, "created_time", pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-31"))
        assert res.empty  # Devuelve DataFrame vacío si no existe la columna

    def test_filtrar_por_fecha_df_none(self):
        """None devuelve DataFrame vacío (no rompe)."""
        res = filtrar_por_fecha(None, "created_time", pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-31"))
        assert res.empty

    def test_filtrar_por_fecha_df_vacio(self):
        """DataFrame vacío devuelve DataFrame vacío."""
        df = pd.DataFrame(columns=["created_time", "valor"])
        res = filtrar_por_fecha(df, "created_time", pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-31"))
        assert res.empty