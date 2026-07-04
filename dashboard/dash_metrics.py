"""Capa de datos y metricas del dashboard (extraida de app.py).

Contiene consultas SQL seguras, carga de engagement/sentimiento/series,
clculos (semaforo, patrones, confianza, narrativas, contagio, viralidad,
correlacion) y la capa de narrativa IA (cascada NIM: DeepSeek -> GLM). Las
rutas de BD activas se resuelven en tiempo de ejecucion via _activas().
"""

import streamlit as st
import sqlite3
import pandas as pd
import logging
import os

from config import (
    FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB,
)


def _activas():
    """Devuelve (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)."""
    return (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)


def safe_query(query: str, db_path: str, params=None) -> pd.DataFrame:
    """Lee SQL devolviendo un DataFrame vacío si la DB/tabla no existe o la query falla."""
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        logging.warning(f"safe_query falló ({db_path}): {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def cargar_externos(db_path):
    posts = safe_query("SELECT * FROM external_posts", db_path)
    if posts.empty:
        return posts
    posts['created_time'] = pd.to_datetime(posts['created_time'], errors='coerce')
    sent = safe_query("SELECT * FROM external_sentimiento", db_path)
    if not sent.empty:
        return posts.merge(sent, on='post_id', how='left')
    posts['score_sentimiento'] = 0.0
    posts['comentario_mas_negativo'] = ''
    return posts


@st.cache_data(ttl=3600, show_spinner=False)
def calcular_contagio_emocional(df_fb):
    """Pure transformation: recibe df_fb ya cargado y filtrado (con columnas:
    post_id, created_time, score_emocional, indice_amor, indice_humor,
    indice_tristeza, total_reacciones, message, categoria_nombre, score_sentimiento,
    pct_positivo, pct_negativo).
    No hace consultas SQL ni filtro de fecha — eso se hace en cargar_engagement_periodo.
    Devuelve (df_posts, conteo_tipos, distorsion_alta, por_semana).
    """
    if df_fb is None or df_fb.empty:
        return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

    # Asegurar columnas necesarias
    req = ["post_id", "created_time", "score_emocional", "sent_comentarios",
           "pct_positivo", "pct_negativo", "categoria_nombre", "message"]
    for c in req:
        if c not in df_fb.columns:
            return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

    df_posts = df_fb.copy()
    df_posts["created_time"] = pd.to_datetime(
        df_posts["created_time"], errors="coerce"
    )
    df_posts["semana"] = df_posts["created_time"].dt.to_period("W").dt.start_time
    df_posts = df_posts.dropna(subset=["created_time"])

    df_posts["distorsion"] = (
        df_posts["score_emocional"] - df_posts["sent_comentarios"]
    )

    umbral_pos = df_posts["score_emocional"].quantile(0.75)
    umbral_neg = df_posts["score_emocional"].quantile(0.25)

    def clasificar_contagio(row):
        em = row.get("score_emocional", 0) or 0
        sent = row.get("sent_comentarios", 0) or 0
        dist = row.get("distorsion", 0) or 0

        if pd.isna(em) or pd.isna(sent):
            return "sin_datos", "Sin datos suficientes"

        if em >= umbral_pos and sent >= umbral_pos:
            return "resonancia_positiva", "Resonancia positiva"
        elif em >= umbral_pos and sent <= umbral_neg:
            return "rechazo_a_positivo", "Rechazo a mensaje positivo"
        elif em <= umbral_neg and sent <= umbral_neg:
            return "resonancia_negativa", "Resonancia negativa"
        elif em <= umbral_neg and sent >= umbral_pos:
            return "inversion_positiva", "Inversión positiva"
        elif abs(dist) > 0.3:
            return "distorsion_alta", "Alta distorsión narrativa"
        else:
            return "neutral", "Respuesta neutral"

    df_posts["tipo_contagio"] = df_posts.apply(
        lambda r: clasificar_contagio(r)[0], axis=1
    )
    df_posts["label_contagio"] = df_posts.apply(
        lambda r: clasificar_contagio(r)[1], axis=1
    )

    conteo_tipos = df_posts["tipo_contagio"].value_counts().to_dict()

    distorsion_alta = df_posts[
        df_posts["tipo_contagio"] == "rechazo_a_positivo"
    ].nlargest(5, "distorsion")[
        ["post_id", "created_time", "message",
         "score_emocional", "sent_comentarios",
         "distorsion", "categoria_nombre"]
    ]

    por_semana = df_posts.groupby("semana").agg(
        score_post=("score_emocional", "mean"),
        score_comentarios=("sent_comentarios", "mean"),
        distorsion_prom=("distorsion", "mean")
    ).reset_index().dropna()

    return df_posts, conteo_tipos, distorsion_alta, por_semana


