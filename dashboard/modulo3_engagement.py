import sqlite3
import pandas as pd
import os
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard.config import *


def _ids_existentes(conn, tabla, col):
    """IDs (col) que ya estan en `tabla`. Set vacio si la tabla no existe.

    Permite procesar SOLO los posts/videos nuevos en cada lote en lugar de
    recomputar toda la base.
    """
    try:
        rows = conn.execute(f"SELECT {col} FROM {tabla}").fetchall()
        return {r[0] for r in rows if r[0] is not None}
    except Exception:
        return set()


def _ids_pendientes_recalculo(conn, tabla, col):
    """IDs marcados con needs_recalculo=1 en tabla. Set vacio si la
    columna/tabla no existe.

    Se usa para forzar el recalculo de un post/video ya procesado cuando
    editor_db.py corrigio manualmente alguno de sus campos de engagement
    (D24): sin esto, _ids_existentes lo excluiria para siempre.
    """
    try:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
        if "needs_recalculo" not in cols:
            return set()
        rows = conn.execute(f"SELECT {col} FROM {tabla} WHERE needs_recalculo = 1").fetchall()
        return {r[0] for r in rows if r[0] is not None}
    except Exception:
        return set()


def procesar_facebook(fb_db=None):
    if fb_db is None:
        fb_db = FACEBOOK_DB
    conn = sqlite3.connect(fb_db)

    placeholders = ",".join(repr(p) for p in FB_PAGES_OFICIALES)
    query = f"""
        SELECT post_id, page_name, created_time, message,
               likes_count, loves_count, cares_count, hahas_count, wows_count,
               sads_count, angrys_count, comments_count
        FROM fb_posts
        WHERE page_name IN ({placeholders})
        AND created_time IS NOT NULL
        AND created_time != ''
    """
    df = pd.read_sql_query(query, conn)

    # Incremental: procesar posts nuevos + posts ya procesados que el
    # analista corrigio manualmente desde el editor (D24: antes esos ultimos
    # quedaban excluidos para siempre por estar ya en fb_engagement).
    existentes = _ids_existentes(conn, "fb_engagement", "post_id")
    pendientes_recalculo = _ids_pendientes_recalculo(conn, "fb_posts", "post_id")
    if existentes:
        antes = len(df)
        a_procesar = ~df["post_id"].isin(existentes) | df["post_id"].isin(pendientes_recalculo)
        df = df[a_procesar].copy()
        print(f"  Incremental: {antes - len(df)} posts ya con engagement al dia se omiten"
              f" ({len(pendientes_recalculo)} marcados para recalculo")

    if df.empty:
        conn.close()
        print("  Facebook: 0 posts nuevos o marcados para recalculo")
        return df

    # Total de reacciones: TODAS las 7 reacciones de Facebook (ninguna queda fuera)
    df["total_reacciones"] = (
        df["likes_count"] + df["loves_count"] + df["cares_count"] + df["hahas_count"]
        + df["wows_count"] + df["sads_count"] + df["angrys_count"]
    )

    def _indice(col):
        return (
            (df[col] / df["total_reacciones"])
            .replace([float("inf"), float("-inf")], 0)
            .fillna(0)
        )

    df["indice_amor"] = _indice("loves_count")
    df["indice_carino"] = _indice("cares_count")
    df["indice_humor"] = _indice("hahas_count")
    df["indice_asombro"] = _indice("wows_count")
    df["indice_tristeza"] = _indice("sads_count")
    df["indice_enojo"] = _indice("angrys_count")
    df["engagement_total"] = df["total_reacciones"] + df["comments_count"]
    # Score emocional neto (valencia de reacciones en contexto civico):
    #   Positivas (afecto/apoyo): Me encanta (amor) + Me importa (carino).
    #   Negativas (rechazo/burla): Me entristece (tristeza) + Me enoja (enojo)
    #     + Me divierte (humor). \"Me divierte\" en publicaciones oficiales es
    #     mayoritariamente burla/sarcasmo, por lo que cuenta como senal
    #     NEGATIVA, nunca positiva.
    #   Neutras/ambiguas (excluidas): Me gusta (base generica) y Me asombra
    #     (asombro, ambiguo: puede ser admiracion o escandalo).
    df["score_emocional"] = (
        (df["indice_amor"] + df["indice_carino"])
        - (df["indice_tristeza"] + df["indice_enojo"] + df["indice_humor"])
    )
    df["plataforma"] = "facebook"

    cols_salida = [
        "post_id", "page_name", "created_time", "message",
        "total_reacciones", "indice_amor", "indice_carino", "indice_humor", "indice_asombro",
        "indice_tristeza", "indice_enojo", "engagement_total",
        "score_emocional", "plataforma"
    ]
    # D24: upsert real — reemplaza la fila de los posts recalculados en vez
    # de duplicarla con un segundo append.
    post_ids_procesados = df["post_id"].tolist()
    placeholders_ids = ",".join("?" for _ in post_ids_procesados)
    try:
        conn.execute(f"DELETE FROM fb_engagement WHERE post_id IN ({placeholders_ids})", post_ids_procesados)
    except sqlite3.OperationalError:
        pass  # la tabla fb_engagement aun no existe en la primera corrida
    df[cols_salida].to_sql("fb_engagement", conn, if_exists="append", index=False)
    ids_limpiar = [pid for pid in post_ids_procesados if pid in pendientes_recalculo]
    if ids_limpiar:
        ph = ",".join("?" for _ in ids_limpiar)
        conn.execute(f"UPDATE fb_posts SET needs_recalculo = 0 WHERE post_id IN ({ph})", ids_limpiar)
    conn.commit()
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

    # Incremental: procesar videos nuevos + videos ya procesados marcados
    # para recalculo (D24, mismo patron que Facebook).
    existentes = _ids_existentes(conn, "tiktok_engagement", "id")
    pendientes_recalculo = _ids_pendientes_recalculo(conn, "videos", "id")
    conn.close()

    if existentes:
        antes = len(df)
        a_procesar = ~df["id"].isin(existentes) | df["id"].isin(pendientes_recalculo)
        df = df[a_procesar].copy()
        print(f"  Incremental: {antes - len(df)} videos ya con engagement al dia se omiten"
              f" ({len(pendientes_recalculo)} marcados para recalculo")

    if df.empty:
        print("  TikTok: 0 videos nuevos o marcados para recalculo")
        return df

    df["engagement_total"] = df["likes"] + df["shares"] + df["comments_count"] + df["favorites_count"]
    df["engagement_rate"] = (df["engagement_total"] / df["views"]).fillna(0).replace([float("inf")], 0)
    df["indice_viralidad"] = (df["shares"] / df["views"]).fillna(0).replace([float("inf")], 0)
    df["score_engagement"] = df["engagement_rate"]
    df["page_name"] = df["account_id"].map(TK_ACCOUNTS).fillna("Desconocido")
    df["plataforma"] = "tiktok"

    cols_salida = [
        "id", "account_id", "page_name", "description", "created_at",
        "views", "likes", "shares", "favorites_count", "comments_count",
        "engagement_total", "engagement_rate", "indice_viralidad",
        "score_engagement", "plataforma"
    ]

    conn = sqlite3.connect(tk_db)
    ids_procesados = df["id"].tolist()
    placeholders_ids = ",".join("?" for _ in ids_procesados)
    try:
        conn.execute(f"DELETE FROM tiktok_engagement WHERE id IN ({placeholders_ids})", ids_procesados)
    except sqlite3.OperationalError:
        pass
    df[cols_salida].to_sql("tiktok_engagement", conn, if_exists="append", index=False)
    ids_limpiar = [vid for vid in ids_procesados if vid in pendientes_recalculo]
    if ids_limpiar:
        ph = ",".join("?" for _ in ids_limpiar)
        conn.execute(f"UPDATE videos SET needs_recalculo = 0 WHERE id IN ({ph})", ids_limpiar)
    conn.commit()
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
