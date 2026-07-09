"""Métricas de engagement para TikTok.

Calcula viralidad y tasas de engagement sobre el DataFrame de videos.
"""

import pandas as pd


def calcular_viralidad_tiktok(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columna engagement_rate al DataFrame de videos TikTok.

    La tasa se calcula como:
        ER = (likes + favorites_count + comments_count + shares) / views

    Corregido para incluir favorites_count que antes se omitía.
    """
    v = df["views"].replace(0, pd.NA).fillna(1)
    df["engagement_rate"] = (
        (df["likes"] + df["favorites_count"] + df["comments_count"] + df["shares"]) / v
    ).fillna(0.0)
    return df
