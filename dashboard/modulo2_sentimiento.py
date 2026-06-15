import sqlite3
import pandas as pd
import os
import sys
sys.path.insert(0, "/Users/pro/Downloads/scrapeo-social/dashboard")
from config import *
import re
from sentimiento_engine import clasificar_lote, analizar_sentimiento_rapido


def limpiar_texto(texto):
    if not texto:
        return None
    texto = texto.lower()
    texto = re.sub(r"http\S+", "", texto)
    texto = re.sub(r"@\w+", "", texto)
    texto = re.sub(r"#\w+", "", texto)
    texto = re.sub(r"[^a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9\s.,!?¿¡]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto:
        return None
    return texto


def analizar_sentimiento_facebook(db_path=None):
    if db_path is None:
        db_path = FACEBOOK_DB
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT comment_id, post_id, message FROM fb_comments WHERE message IS NOT NULL AND message != ''",
        conn,
    )

    total_raw = len(df)
    df["texto_limpio"] = df["message"].apply(limpiar_texto)
    df = df[df["texto_limpio"].notna()].copy()
    df["num_palabras"] = df["texto_limpio"].str.split().str.len()
    df = df[df["num_palabras"] >= 3].copy()
    print(f"  ({total_raw} comentarios crudos → {len(df)} para análisis)")

    resultados = []
    textos = df["texto_limpio"].tolist()
    labels_scores, motor_usado = clasificar_lote(textos)
    for (label, score), (_, row) in zip(labels_scores, df.iterrows()):
        resultados.append({
            "comment_id": row["comment_id"],
            "post_id": row["post_id"],
            "message": row["message"],
            "label": label,
            "score": score,
        })

    conn.close()

    if not resultados:
        print("  Sin resultados de sentimiento")
        return pd.DataFrame(), motor_usado

    df_res = pd.DataFrame(resultados)

    total = len(df_res)
    for label in ["POS", "NEG", "NEU"]:
        pct = (df_res["label"] == label).sum() / total * 100
        print(f"    {label}: {pct:.1f}%")

    def _top_comment_by_neg(group):
        idx = group["label"].value_counts().get("NEG", 0)
        neg_rows = group[group["label"] == "NEG"]
        if not neg_rows.empty:
            top = neg_rows.loc[neg_rows["score"].idxmax()]
            return top["message"][:200]
        return ""

    def _top_comment_by_pos(group):
        pos_rows = group[group["label"] == "POS"]
        if not pos_rows.empty:
            top = pos_rows.loc[pos_rows["score"].idxmax()]
            return top["message"][:200]
        return ""

    agrupado = df_res.groupby("post_id").agg(
        total_comentarios=("comment_id", "count"),
        pct_positivo=("label", lambda x: (x == "POS").sum() / max(len(x), 1) * 100),
        pct_negativo=("label", lambda x: (x == "NEG").sum() / max(len(x), 1) * 100),
        pct_neutral=("label", lambda x: (x == "NEU").sum() / max(len(x), 1) * 100),
        comentario_mas_negativo=("post_id", lambda pid: _top_comment_by_neg(df_res[df_res["post_id"] == pid.iloc[0]])),
        comentario_mas_positivo=("post_id", lambda pid: _top_comment_by_pos(df_res[df_res["post_id"] == pid.iloc[0]])),
    ).reset_index()

    agrupado["score_sentimiento"] = agrupado["pct_positivo"] - agrupado["pct_negativo"]

    conn = sqlite3.connect(db_path)
    agrupado.to_sql("fb_sentimiento", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  Posts agrupados: {len(agrupado)}")
    return agrupado, motor_usado


def analizar_sentimiento_tiktok(db_path=None):
    if db_path is None:
        db_path = TIKTOK_DB
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT id as comment_id, video_id, text as message FROM comments WHERE text IS NOT NULL AND text != ''",
        conn,
    )
    conn.close()

    total_raw = len(df)
    if total_raw == 0:
        print("  No hay comentarios en TikTok DB")
        return pd.DataFrame(), "reglas"

    df["texto_limpio"] = df["message"].apply(limpiar_texto)
    df = df[df["texto_limpio"].notna()].copy()
    df["num_palabras"] = df["texto_limpio"].str.split().str.len()
    df = df[df["num_palabras"] >= 3].copy()
    print(f"  ({total_raw} comentarios crudos → {len(df)} para análisis)")

    resultados = []
    textos = df["texto_limpio"].tolist()
    labels_scores, motor_usado = clasificar_lote(textos)
    for (label, score), (_, row) in zip(labels_scores, df.iterrows()):
        resultados.append({
            "comment_id": row["comment_id"],
            "video_id": row["video_id"],
            "message": row["message"],
            "label": label,
            "score": score,
        })

    if not resultados:
        print("  Sin resultados de sentimiento")
        return pd.DataFrame(), motor_usado

    df_res = pd.DataFrame(resultados)

    total = len(df_res)
    for label in ["POS", "NEG", "NEU"]:
        pct = (df_res["label"] == label).sum() / total * 100
        print(f"    {label}: {pct:.1f}%")

    def _top_comment_by_neg(group):
        neg_rows = group[group["label"] == "NEG"]
        if not neg_rows.empty:
            top = neg_rows.loc[neg_rows["score"].idxmax()]
            return top["message"][:200]
        return ""

    def _top_comment_by_pos(group):
        pos_rows = group[group["label"] == "POS"]
        if not pos_rows.empty:
            top = pos_rows.loc[pos_rows["score"].idxmax()]
            return top["message"][:200]
        return ""

    agrupado = df_res.groupby("video_id").agg(
        total_comentarios=("comment_id", "count"),
        pct_positivo=("label", lambda x: (x == "POS").sum() / max(len(x), 1) * 100),
        pct_negativo=("label", lambda x: (x == "NEG").sum() / max(len(x), 1) * 100),
        pct_neutral=("label", lambda x: (x == "NEU").sum() / max(len(x), 1) * 100),
        comentario_mas_negativo=("video_id", lambda vid: _top_comment_by_neg(df_res[df_res["video_id"] == vid.iloc[0]])),
        comentario_mas_positivo=("video_id", lambda vid: _top_comment_by_pos(df_res[df_res["video_id"] == vid.iloc[0]])),
    ).reset_index()

    agrupado["score_sentimiento"] = agrupado["pct_positivo"] - agrupado["pct_negativo"]

    conn = sqlite3.connect(db_path)
    agrupado.to_sql("tiktok_sentimiento", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  Videos agrupados: {len(agrupado)}")
    return agrupado, motor_usado


def imprimir_resultados(df_fb, df_tk):
    print("\n=== SENTIMIENTO FACEBOOK ===")
    if not df_fb.empty:
        total_comments = int(df_fb["total_comentarios"].sum())
        total_pos = (df_fb["pct_positivo"] * df_fb["total_comentarios"] / 100).sum()
        total_neg = (df_fb["pct_negativo"] * df_fb["total_comentarios"] / 100).sum()
        total_neu = (df_fb["pct_neutral"] * df_fb["total_comentarios"] / 100).sum()
        pct_pos = total_pos / total_comments * 100 if total_comments else 0
        pct_neg = total_neg / total_comments * 100 if total_comments else 0
        pct_neu = total_neu / total_comments * 100 if total_comments else 0
        print(f"Total comentarios analizados: {total_comments}")
        print(f"Distribución global: {pct_pos:.1f}% positivo / {pct_neg:.1f}% negativo / {pct_neu:.1f}% neutral")

        print("\nPosts más negativos (top 3):")
        top_neg = df_fb.nlargest(3, "pct_negativo")
        for _, row in top_neg.iterrows():
            msg = (row.get("comentario_mas_negativo", "") or "")[:80].replace("\n", " ")
            print(f'  - {row["post_id"][:40]}... score: -{abs(row["score_sentimiento"]):.2f} → "{msg}"')

        print("\nPosts más positivos (top 3):")
        top_pos = df_fb.nlargest(3, "pct_positivo")
        for _, row in top_pos.iterrows():
            msg = (row.get("comentario_mas_positivo", "") or "")[:80].replace("\n", " ")
            print(f'  - {row["post_id"][:40]}... score: +{row["score_sentimiento"]:.2f} → "{msg}"')
    else:
        print("Sin datos de Facebook")

    print("\n=== SENTIMIENTO TIKTOK ===")
    if not df_tk.empty:
        total_comments = int(df_tk["total_comentarios"].sum())
        total_pos = (df_tk["pct_positivo"] * df_tk["total_comentarios"] / 100).sum()
        total_neg = (df_tk["pct_negativo"] * df_tk["total_comentarios"] / 100).sum()
        total_neu = (df_tk["pct_neutral"] * df_tk["total_comentarios"] / 100).sum()
        pct_pos = total_pos / total_comments * 100 if total_comments else 0
        pct_neg = total_neg / total_comments * 100 if total_comments else 0
        pct_neu = total_neu / total_comments * 100 if total_comments else 0
        print(f"Total comentarios analizados: {total_comments}")
        print(f"Distribución global: {pct_pos:.1f}% positivo / {pct_neg:.1f}% negativo / {pct_neu:.1f}% neutral")

        print("\nVideos más negativos (top 3):")
        top_neg = df_tk.nlargest(3, "pct_negativo")
        for _, row in top_neg.iterrows():
            msg = (row.get("comentario_mas_negativo", "") or "")[:80].replace("\n", " ")
            print(f'  - {row["video_id"][:40]}... score: -{abs(row["score_sentimiento"]):.2f} → "{msg}"')

        print("\nVideos más positivos (top 3):")
        top_pos = df_tk.nlargest(3, "pct_positivo")
        for _, row in top_pos.iterrows():
            msg = (row.get("comentario_mas_positivo", "") or "")[:80].replace("\n", " ")
            print(f'  - {row["video_id"][:40]}... score: +{row["score_sentimiento"]:.2f} → "{msg}"')
    else:
        print("Sin datos de TikTok")


if __name__ == "__main__":
    print("▶ Analizando sentimiento Facebook...")
    print("  (usando clasificador rápido basado en reglas)")
    df_fb, motor_fb = analizar_sentimiento_facebook()
    print(f"  Motor usado: {motor_fb}")
    print("▶ Analizando sentimiento TikTok...")
    df_tk, motor_tk = analizar_sentimiento_tiktok()
    print(f"  Motor usado: {motor_tk}")
    imprimir_resultados(df_fb, df_tk)
    print("✓ Módulo 2 completo.")
