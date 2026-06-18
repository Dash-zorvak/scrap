import sqlite3
import pandas as pd
import os
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *


def procesar_facebook(fb_db=None):
    if fb_db is None:
        fb_db = FACEBOOK_DB
    conn = sqlite3.connect(fb_db)

    placeholders = ",".join(repr(p) for p in FB_PAGES_OFICIALES)
    query = f"""
        SELECT post_id, page_name, created_time, message,
               likes_count, loves_count, hahas_count, wows_count,
               sads_count, angrys_count, comments_count
        FROM fb_posts
        WHERE page_name IN ({placeholders})
        AND created_time IS NOT NULL
        AND created_time != ''
    """
    df = pd.read_sql_query(query, conn)

    # Total de reacciones: TODAS las 6 reacciones de Facebook (ninguna queda fuera)
    df["total_reacciones"] = (
        df["likes_count"] + df["loves_count"] + df["hahas_count"]
        + df["wows_count"] + df["sads_count"] + df["angrys_count"]
    )

    def _indice(col):
        return (
            (df[col] / df["total_reacciones"])
            .replace([float("inf"), float("-inf")], 0)
            .fillna(0)
        )

    df["indice_amor"] = _indice("loves_count")
    df["indice_humor"] = _indice("hahas_count")
    df["indice_asombro"] = _indice("wows_count")
    df["indice_tristeza"] = _indice("sads_count")
    df["indice_enojo"] = _indice("angrys_count")
    df["engagement_total"] = df["total_reacciones"] + df["comments_count"]
    # Score emocional neto: afecto positivo (amor + asombro) menos carga negativa (tristeza + enojo)
    df["score_emocional"] = (
        (df["indice_amor"] + df["indice_asombro"])
        - (df["indice_tristeza"] + df["indice_enojo"])
    )
    df["plataforma"] = "facebook"

    df = df[df["total_reacciones"] >= 10].copy()

    cols_salida = [
        "post_id", "page_name", "created_time", "message",
        "total_reacciones", "indice_amor", "indice_humor", "indice_asombro",
        "indice_tristeza", "indice_enojo", "engagement_total",
        "score_emocional", "plataforma"
    ]
    df[cols_salida].to_sql("fb_engagement", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  Facebook: {len(df)} posts procesados")
    return df


def procesar_tiktok(tk_db=None):
    if tk_db is None:
        tk_db = TIKTOK_DB
    conn = sqlite3.connect(tk_db)

    query = """
        SELECT id, account_id, description, created_at,
               views, likes, shares, favorites_count, comments_count
        FROM videos
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["engagement_total"] = df["likes"] + df["shares"] + df["comments_count"] + df["favorites_count"]
    df["engagement_rate"] = (df["engagement_total"] / df["views"]).fillna(0).replace([float("inf")], 0)
    df["indice_viralidad"] = (df["shares"] / df["views"]).fillna(0).replace([float("inf")], 0)
    df["score_engagement"] = df["engagement_rate"]
    df["page_name"] = df["account_id"].map(TK_ACCOUNTS).fillna("Desconocido")
    df["plataforma"] = "tiktok"

    df = df[df["views"] >= 100].copy()

    cols_salida = [
        "id", "account_id", "page_name", "description", "created_at",
        "views", "likes", "shares", "favorites_count", "comments_count",
        "engagement_total", "engagement_rate", "indice_viralidad",
        "score_engagement", "plataforma"
    ]

    conn = sqlite3.connect(tk_db)
    df[cols_salida].to_sql("tiktok_engagement", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  TikTok: {len(df)} videos procesados")
    return df


def imprimir_resultados(df_fb, df_tk):
    print("\n=== FACEBOOK ===")
    print(f"Total posts procesados: {len(df_fb)}")
    if not df_fb.empty:
        print(f"Rango de fechas: {df_fb['created_time'].min()[:10]} a {df_fb['created_time'].max()[:10]}")

        print("Top 5 posts por score_emocional (amor):")
        top_amor = df_fb.nlargest(5, "score_emocional")
        for _, row in top_amor.iterrows():
            msg = (row["message"] or "")[:80].replace("\n", " ")
            print(f'  - [{row["created_time"][:10]}] [{row["page_name"]}] {msg} \u2192 score: {row["score_emocional"]:.2f}')

        print("Top 5 posts por indice_humor:")
        top_humor = df_fb.nlargest(5, "indice_humor")
        for _, row in top_humor.iterrows():
            msg = (row["message"] or "")[:80].replace("\n", " ")
            print(f'  - [{row["created_time"][:10]}] [{row["page_name"]}] {msg} \u2192 humor: {row["indice_humor"]:.2f}')

    print("\n=== TIKTOK ===")
    print(f"Total videos procesados: {len(df_tk)}")
    if not df_tk.empty:
        print(f"Rango de fechas: {df_tk['created_at'].min()[:10]} a {df_tk['created_at'].max()[:10]}")

        print("Top 5 videos por engagement_rate:")
        top_er = df_tk.nlargest(5, "engagement_rate")
        for _, row in top_er.iterrows():
            desc = (row["description"] or "")[:80].replace("\n", " ")
            print(f'  - [{row["created_at"][:10]}] [{row["page_name"]}] {desc} \u2192 rate: {row["engagement_rate"]*100:.2f}%')

        print("Top 5 videos por indice_viralidad:")
        top_vir = df_tk.nlargest(5, "indice_viralidad")
        for _, row in top_vir.iterrows():
            desc = (row["description"] or "")[:80].replace("\n", " ")
            print(f'  - [{row["created_at"][:10]}] [{row["page_name"]}] {desc} \u2192 viral: {row["indice_viralidad"]*100:.2f}%')


if __name__ == "__main__":
    print("\u25b6 Procesando Facebook...")
    df_fb = procesar_facebook()
    print("\u25b6 Procesando TikTok...")
    df_tk = procesar_tiktok()
    imprimir_resultados(df_fb, df_tk)
    print("\u2713 M\u00f3dulo 3 completo. Tablas guardadas en SQLite.")
