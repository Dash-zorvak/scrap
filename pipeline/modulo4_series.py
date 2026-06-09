import logging
import sqlite3

import numpy as np
import pandas as pd

from pipeline.config import PIPELINE_DB, OUTPUT_DIR, ROLLING_WINDOW, ANOMALY_STD_THRESHOLD
from pipeline.create_views import get_db, FB_POSTS_QUERY, TT_POSTS_QUERY

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

HAS_SCIPY = False
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    pass


def cargar_series() -> pd.DataFrame:
    conn = get_db()

    fb = pd.read_sql(f"""
        SELECT id, plataforma, fecha,
               (me_gusta+me_encanta+me_divierte+me_asombra+me_entristece+me_enoja+compartidos) AS engagement,
               me_enoja, me_entristece, compartidos, views
        FROM ({FB_POSTS_QUERY}) WHERE fecha IS NOT NULL
    """, conn)

    tt = pd.read_sql(f"""
        SELECT id, plataforma, fecha,
               (me_gusta+compartidos) AS engagement,
               0 AS me_enoja, 0 AS me_entristece, compartidos, views
        FROM ({TT_POSTS_QUERY}) WHERE fecha IS NOT NULL
    """, conn)

    conn.close()

    df = pd.concat([fb, tt], ignore_index=True)

    for col in ["fecha"]:
        try:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        except:
            pass

    df = df.dropna(subset=["fecha"]).sort_values("fecha")
    log.info(f"Series cargadas: {len(df)} posts con fecha")
    return df


def agregar_semanal(df: pd.DataFrame) -> pd.DataFrame:
    df["semana"] = df["fecha"].dt.isocalendar().week.astype(int)
    df["año"] = df["fecha"].dt.year
    df["periodo"] = df["año"].astype(str) + "-W" + df["semana"].astype(str).str.zfill(2)
    df["periodo_dt"] = df["fecha"] - pd.to_timedelta(df["fecha"].dt.dayofweek, unit="D")

    semana_plataforma = df.groupby(["periodo_dt", "periodo", "plataforma"]).agg(
        total_posts=("id", "count"),
        engagement_total=("engagement", "sum"),
        engagement_promedio=("engagement", "mean"),
        controversia_total=("me_enoja", "sum"),
        viralidad_promedio=("compartidos", "mean"),
    ).reset_index()

    semana_plataforma = semana_plataforma.sort_values("periodo_dt")
    semana_plataforma["semana_label"] = semana_plataforma["periodo_dt"].dt.strftime("%Y-%m-%d")
    return semana_plataforma


def detectar_anomalias(df_semanal: pd.DataFrame, col: str = "engagement_promedio") -> pd.DataFrame:
    df = df_semanal.copy()
    df["media_movil"] = df[col].rolling(window=ROLLING_WINDOW, min_periods=2).mean()
    df["std_movil"] = df[col].rolling(window=ROLLING_WINDOW, min_periods=2).std()

    df["es_anomalia"] = False
    df["tipo_anomalia"] = ""

    for i in range(len(df)):
        if pd.isna(df.loc[i, "media_movil"]) or pd.isna(df.loc[i, "std_movil"]):
            continue
        if df.loc[i, "std_movil"] == 0:
            continue
        z = (df.loc[i, col] - df.loc[i, "media_movil"]) / df.loc[i, "std_movil"]
        if abs(z) > ANOMALY_STD_THRESHOLD:
            df.loc[i, "es_anomalia"] = True
            df.loc[i, "tipo_anomalia"] = "pico_positivo" if z > 0 else "pico_negativo"

    n_anomalias = df["es_anomalia"].sum()
    log.info(f"  Anomalías detectadas: {n_anomalias} de {len(df)} semanas")

    if HAS_SCIPY and len(df) > 3:
        zscores = np.abs(scipy_stats.zscore(df[col].dropna()))
        outliers = np.where(zscores > ANOMALY_STD_THRESHOLD)[0]
        log.info(f"  (scipy) Outliers adicionales: {len(outliers)}")

    return df


def guardar_resultados(post_series: pd.DataFrame, semanal: pd.DataFrame, anomalias: pd.DataFrame):
    conn = sqlite3.connect(PIPELINE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS series_temporales (
            periodo TEXT,
            plataforma TEXT,
            semana_label TEXT,
            total_posts INTEGER,
            engagement_total INTEGER,
            engagement_promedio REAL,
            controversia_total INTEGER,
            viralidad_promedio REAL,
            media_movil REAL,
            es_anomalia INTEGER,
            tipo_anomalia TEXT
        )
    """)
    conn.execute("DELETE FROM series_temporales")
    cols = ["periodo", "plataforma", "semana_label", "total_posts",
            "engagement_total", "engagement_promedio", "controversia_total",
            "viralidad_promedio", "media_movil", "es_anomalia", "tipo_anomalia"]
    anomalias_filtered = anomalias[[c for c in cols if c in anomalias.columns]]
    anomalias_filtered.to_sql("series_temporales", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

    semanal.to_csv(f"{OUTPUT_DIR}/series_semanal.csv", index=False)
    anomalias.to_csv(f"{OUTPUT_DIR}/series_anomalias.csv", index=False)
    log.info(f"Resultados guardados: {len(anomalias)} registros en series_temporales + CSV")


def run():
    log.info("=" * 50)
    log.info("MÓDULO 4 — Series temporales y detección de anomalías")
    log.info("=" * 50)

    df = cargar_series()
    semanal = agregar_semanal(df)
    anomalias = detectar_anomalias(semanal)
    guardar_resultados(df, semanal, anomalias)
    log.info("Módulo 4 completado.")
    return anomalias


if __name__ == "__main__":
    run()
