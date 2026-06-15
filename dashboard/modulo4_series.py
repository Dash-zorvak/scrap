import sqlite3
import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, "/Users/pro/Downloads/scrapeo-social/dashboard")
from config import *


def series_facebook(fb_db=None):
    if fb_db is None:
        fb_db = FACEBOOK_DB
    conn = sqlite3.connect(fb_db)
    df = pd.read_sql_query("SELECT * FROM fb_engagement", conn)

    df["created_time"] = pd.to_datetime(df["created_time"], errors="coerce")
    df = df.dropna(subset=["created_time"])

    df["semana"] = df["created_time"] - pd.to_timedelta(df["created_time"].dt.dayofweek, unit="D")
    df["semana"] = df["semana"].dt.floor("D")

    agrupado = df.groupby("semana").agg(
        total_posts=("engagement_total", "count"),
        engagement_promedio=("engagement_total", "mean"),
        score_emocional_promedio=("score_emocional", "mean"),
        indice_amor_promedio=("indice_amor", "mean"),
        indice_humor_promedio=("indice_humor", "mean"),
        indice_tristeza_promedio=("indice_tristeza", "mean"),
        total_reacciones_suma=("total_reacciones", "sum"),
    ).reset_index()

    agrupado["media_movil_4s"] = agrupado["engagement_promedio"].rolling(window=4, min_periods=1).mean()

    media_global = agrupado["engagement_promedio"].mean()
    std_global = agrupado["engagement_promedio"].std()
    agrupado["es_anomalia"] = (
        (agrupado["engagement_promedio"] > media_global + 2 * std_global) |
        (agrupado["engagement_promedio"] < media_global - 2 * std_global)
    )

    agrupado["plataforma"] = "facebook"

    agrupado.to_sql("series_facebook", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  Facebook: {len(agrupado)} semanas")
    return agrupado


def series_tiktok(tk_db=None):
    if tk_db is None:
        tk_db = TIKTOK_DB
    conn = sqlite3.connect(tk_db)
    df = pd.read_sql_query("SELECT * FROM tiktok_engagement", conn)

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.dropna(subset=["created_at"])

    df["semana"] = df["created_at"] - pd.to_timedelta(df["created_at"].dt.dayofweek, unit="D")
    df["semana"] = df["semana"].dt.floor("D")

    agrupado = df.groupby("semana").agg(
        total_videos=("id", "count"),
        views_suma=("views", "sum"),
        engagement_promedio=("engagement_total", "mean"),
        engagement_rate_promedio=("engagement_rate", "mean"),
        indice_viralidad_promedio=("indice_viralidad", "mean"),
        likes_suma=("likes", "sum"),
        shares_suma=("shares", "sum"),
    ).reset_index()

    agrupado["media_movil_4s"] = agrupado["views_suma"].rolling(window=4, min_periods=1).mean()

    media_global = agrupado["views_suma"].mean()
    std_global = agrupado["views_suma"].std()
    agrupado["es_anomalia"] = (
        (agrupado["views_suma"] > media_global + 2 * std_global) |
        (agrupado["views_suma"] < media_global - 2 * std_global)
    )

    agrupado["plataforma"] = "tiktok"

    agrupado.to_sql("series_tiktok", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  TikTok: {len(agrupado)} semanas")
    return agrupado


def imprimir_resultados(df_fb, df_tk):
    print("\n=== SERIES TEMPORALES FACEBOOK ===")
    print(f"Total semanas: {len(df_fb)}")

    anomalias_fb = df_fb[df_fb["es_anomalia"]]
    print(f"Semanas con anomalía detectada: {len(anomalias_fb)}")
    if not anomalias_fb.empty:
        print("Anomalías (semanas inusuales):")
        for _, row in anomalias_fb.iterrows():
            tipo = "PICO POSITIVO" if row["engagement_promedio"] > df_fb["engagement_promedio"].mean() else "CAÍDA"
            print(f"  - Semana {row['semana'].strftime('%Y-%m-%d')}: "
                  f"engagement={row['engagement_promedio']:.1f} — {tipo}")
            print(f"    (score emocional esa semana: {row['score_emocional_promedio']:.2f})")

    print("\n=== SERIES TEMPORALES TIKTOK ===")
    print(f"Total semanas: {len(df_tk)}")

    anomalias_tk = df_tk[df_tk["es_anomalia"]]
    print(f"Semanas con anomalía detectada: {len(anomalias_tk)}")
    if not anomalias_tk.empty:
        print("Anomalías:")
        for _, row in anomalias_tk.iterrows():
            tipo = "PICO POSITIVO" if row["views_suma"] > df_tk["views_suma"].mean() else "CAÍDA"
            print(f"  - Semana {row['semana'].strftime('%Y-%m-%d')}: "
                  f"views={row['views_suma']:,.0f} — {tipo}")
            print(f"    (engagement_rate esa semana: {row['engagement_rate_promedio']*100:.2f}%)")


if __name__ == "__main__":
    print("▶ Procesando series temporales Facebook...")
    df_fb = series_facebook()
    print("▶ Procesando series temporales TikTok...")
    df_tk = series_tiktok()
    imprimir_resultados(df_fb, df_tk)
    print("✓ Módulo 4 completo.")
