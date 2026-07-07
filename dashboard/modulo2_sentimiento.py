import sqlite3
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard.config import *
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


def _ids_ya_procesados(db_path, tabla, col):
    """IDs (col) que ya tienen resultado en `tabla`. Set vacio si la tabla no existe.

    Es la base de la incrementalidad: permite saltarse los posts/videos que ya
    fueron analizados en lotes anteriores y procesar SOLO lo nuevo.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(f"SELECT DISTINCT {col} FROM {tabla}").fetchall()
        return {r[0] for r in rows if r[0] is not None}
    except Exception:
        return set()
    finally:
        if conn is not None:
            conn.close()


def analizar_sentimiento_facebook(db_path=None):
    if db_path is None:
        db_path = FACEBOOK_DB
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT comment_id, post_id, message FROM fb_comments WHERE message IS NOT NULL AND message != ''",
        conn,
    )
    conn.close()

    # D23: incremental por COMENTARIO, no por post completo. Antes, un post con
    # UNA sola fila en fb_sentimiento quedaba excluido para siempre del
    # recalculo, aunque llegaran comentarios nuevos en una carga posterior.
    # Ahora se salta unicamente los comentarios que ya tienen sentimiento
    # calculado (fb_comments.sentiment), sin importar el estado de su post.
    conn_chk = sqlite3.connect(db_path)
    cur_chk = conn_chk.cursor()
    cols_chk = {row[1] for row in cur_chk.execute("PRAGMA table_info(fb_comments)").fetchall()}
    if "sentiment" not in cols_chk:
        cur_chk.execute("ALTER TABLE fb_comments ADD COLUMN sentiment TEXT")
    if "sentiment_score" not in cols_chk:
        cur_chk.execute("ALTER TABLE fb_comments ADD COLUMN sentiment_score REAL")
    conn_chk.commit()
    ya_clasificados = {
        r[0] for r in cur_chk.execute(
            "SELECT comment_id FROM fb_comments WHERE sentiment IS NOT NULL"
        ).fetchall()
    }
    conn_chk.close()
    if ya_clasificados:
        antes = len(df)
        df = df[~df["comment_id"].isin(ya_clasificados)].copy()
        print(f"  Incremental: {antes - len(df)} comentarios ya clasificados se omiten")

    total_raw = len(df)
    if total_raw == 0:
        print("  Sin comentarios nuevos que analizar (Facebook)")
        return pd.DataFrame(), "reglas"

    df["texto_limpio"] = df["message"].apply(limpiar_texto)
    df = df[df["texto_limpio"].notna()].copy()
    df["num_palabras"] = df["texto_limpio"].str.split().str.len()
    df = df[df["num_palabras"] >= 3].copy()
    print(f"  ({total_raw} comentarios nuevos → {len(df)} para análisis)")

    if df.empty:
        print("  Sin comentarios analizables en los comentarios nuevos")
        return pd.DataFrame(), "reglas"

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

    if not resultados:
        print("  Sin resultados de sentimiento")
        return pd.DataFrame(), motor_usado

    df_res = pd.DataFrame(resultados)

    # Persistir el sentimiento por comentario ANTES de recalcular agregados:
    # es la base de la incrementalidad por comentario (D23) y le da a
    # Facebook paridad con TikTok (_persistir_sentimiento_comentarios_tiktok).
    _persistir_sentimiento_comentarios_facebook(db_path, df_res)

    total = len(df_res)
    for label in ["POS", "NEG", "NEU"]:
        pct = (df_res["label"] == label).sum() / total * 100
        print(f"    {label}: {pct:.1f}%")

    # D23: el agregado por post debe reflejar TODOS sus comentarios ya
    # clasificados (viejos + nuevos), no solo los clasificados en esta
    # corrida — si no, un post con comentarios viejos + nuevos quedaria con
    # un porcentaje calculado solo sobre los nuevos.
    post_ids_afectados = sorted(set(df_res["post_id"]))
    placeholders = ",".join("?" for _ in post_ids_afectados)
    conn_full = sqlite3.connect(db_path)
    df_full = pd.read_sql_query(
        f"""
        SELECT comment_id, post_id, message, sentiment AS etiqueta_es,
               sentiment_score AS score_con_signo
        FROM fb_comments
        WHERE post_id IN ({placeholders}) AND sentiment IS NOT NULL
        """,
        conn_full,
        params=post_ids_afectados,
    )
    conn_full.close()
    _map_inv = {"positivo": "POS", "negativo": "NEG", "neutral": "NEU"}
    df_full["label"] = df_full["etiqueta_es"].map(_map_inv).fillna("NEU")
    df_full["score"] = df_full["score_con_signo"].abs()

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

    agrupado = df_full.groupby("post_id").agg(
        total_comentarios=("comment_id", "count"),
        pct_positivo=("label", lambda x: (x == "POS").sum() / max(len(x), 1) * 100),
        pct_negativo=("label", lambda x: (x == "NEG").sum() / max(len(x), 1) * 100),
        pct_neutral=("label", lambda x: (x == "NEU").sum() / max(len(x), 1) * 100),
        comentario_mas_negativo=("post_id", lambda pid: _top_comment_by_neg(df_full[df_full["post_id"] == pid.iloc[0]])),
        comentario_mas_positivo=("post_id", lambda pid: _top_comment_by_pos(df_full[df_full["post_id"] == pid.iloc[0]])),
    ).reset_index()

    agrupado["score_sentimiento"] = agrupado["pct_positivo"] - agrupado["pct_negativo"]

    # D23: upsert real en vez de append puro — los posts que YA tenian fila en
    # fb_sentimiento se reemplazan con el agregado recalculado (que ahora
    # incluye sus comentarios nuevos), en vez de quedar congelados o
    # duplicados.
    conn_up = sqlite3.connect(db_path)
    try:
        conn_up.execute(
            f"DELETE FROM fb_sentimiento WHERE post_id IN ({placeholders})",
            post_ids_afectados,
        )
    except sqlite3.OperationalError:
        pass  # la tabla fb_sentimiento aun no existe en la primera corrida
    agrupado.to_sql("fb_sentimiento", conn_up, if_exists="append", index=False)
    conn_up.commit()
    conn_up.close()

    print(f"  Posts actualizados (nuevos o con comentarios nuevos): {len(agrupado)}")
    return agrupado, motor_usado


def _persistir_sentimiento_comentarios_tiktok(db_path, df_res):
    """Persiste el sentimiento por comentario en comments.sentiment/sentiment_score.

    El dashboard lee el sentimiento de TikTok comentario por comentario (igual que
    en Facebook, a traves de dash_fuente). El scraper original de TikTok no guarda
    esas columnas, asi que aqui se crean si faltan y se rellenan con el resultado
    del clasificador.

    Mapeo de etiquetas -> dashboard.dash_fuente.clasificar_comentario:
      POS -> \"positivo\"  (score positivo)
      NEG -> \"negativo\"  (score negativo)
      NEU -> \"neutral\"   (score 0)
    El score se guarda con signo para que clasificar_comentario lo interprete.
    """
    if df_res is None or df_res.empty or "comment_id" not in df_res.columns:
        return
    _map = {"POS": "positivo", "NEG": "negativo", "NEU": "neutral"}
    filas = []
    for _, r in df_res.iterrows():
        label = str(r.get("label", "NEU"))
        etiqueta = _map.get(label, "neutral")
        try:
            mag = abs(float(r.get("score", 0)))
        except (TypeError, ValueError):
            mag = 0.0
        if label == "POS":
            score = mag
        elif label == "NEG":
            score = -mag
        else:
            score = 0.0
        filas.append((etiqueta, score, r.get("comment_id")))
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cols = {row[1] for row in cur.execute("PRAGMA table_info(comments)").fetchall()}
        if "sentiment" not in cols:
            cur.execute("ALTER TABLE comments ADD COLUMN sentiment TEXT")
        if "sentiment_score" not in cols:
            cur.execute("ALTER TABLE comments ADD COLUMN sentiment_score REAL")
        cur.executemany(
            "UPDATE comments SET sentiment = ?, sentiment_score = ? WHERE id = ?",
            filas,
        )
        conn.commit()
        print(f"  Sentimiento por comentario TikTok persistido: {len(filas)} filas")
    except Exception as e:
        print(f"  Aviso: no se pudo persistir sentimiento por comentario TikTok: {e}")
    finally:
        if conn is not None:
            conn.close()


def _persistir_sentimiento_comentarios_facebook(db_path, df_res):
    """Persiste el sentimiento por comentario en fb_comments.sentiment/sentiment_score.

    Le da a Facebook la misma granularidad por comentario que ya tiene TikTok
    (ver _persistir_sentimiento_comentarios_tiktok) y es la base de la
    incrementalidad por comentario del fix de D23: permite saber exactamente
    que comentarios ya fueron clasificados sin depender de si el post_id ya
    tiene o no una fila en fb_sentimiento.
    """
    if df_res is None or df_res.empty or "comment_id" not in df_res.columns:
        return
    _map = {"POS": "positivo", "NEG": "negativo", "NEU": "neutral"}
    filas = []
    for _, r in df_res.iterrows():
        label = str(r.get("label", "NEU"))
        etiqueta = _map.get(label, "neutral")
        try:
            mag = abs(float(r.get("score", 0)))
        except (TypeError, ValueError):
            mag = 0.0
        if label == "POS":
            score = mag
        elif label == "NEG":
            score = -mag
        else:
            score = 0.0
        filas.append((etiqueta, score, r.get("comment_id")))
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cols = {row[1] for row in cur.execute("PRAGMA table_info(fb_comments)").fetchall()}
        if "sentiment" not in cols:
            cur.execute("ALTER TABLE fb_comments ADD COLUMN sentiment TEXT")
        if "sentiment_score" not in cols:
            cur.execute("ALTER TABLE fb_comments ADD COLUMN sentiment_score REAL")
        cur.executemany(
            "UPDATE fb_comments SET sentiment = ?, sentiment_score = ? WHERE comment_id = ?",
            filas,
        )
        conn.commit()
        print(f"  Sentimiento por comentario Facebook persistido: {len(filas)} filas")
    except Exception as e:
        print(f"  Aviso: no se pudo persistir sentimiento por comentario Facebook: {e}")
    finally:
        if conn is not None:
            conn.close()


def analizar_sentimiento_tiktok(db_path=None):
    if db_path is None:
        db_path = TIKTOK_DB
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT id as comment_id, video_id, text as message FROM comments WHERE text IS NOT NULL AND text != ''",
        conn,
    )
    conn.close()

    # D23: incremental por COMENTARIO, no por video completo (mismo fix que
    # Facebook). Se reutiliza comments.sentiment, que ya existia gracias a
    # _persistir_sentimiento_comentarios_tiktok, pero antes solo se llenaba
    # para videos nunca vistos.
    conn_chk = sqlite3.connect(db_path)
    cur_chk = conn_chk.cursor()
    cols_chk = {row[1] for row in cur_chk.execute("PRAGMA table_info(comments)").fetchall()}
    if "sentiment" not in cols_chk:
        cur_chk.execute("ALTER TABLE comments ADD COLUMN sentiment TEXT")
    if "sentiment_score" not in cols_chk:
        cur_chk.execute("ALTER TABLE comments ADD COLUMN sentiment_score REAL")
    conn_chk.commit()
    ya_clasificados = {
        r[0] for r in cur_chk.execute(
            "SELECT id FROM comments WHERE sentiment IS NOT NULL"
        ).fetchall()
    }
    conn_chk.close()
    if ya_clasificados:
        antes = len(df)
        df = df[~df["comment_id"].isin(ya_clasificados)].copy()
        print(f"  Incremental: {antes - len(df)} comentarios ya clasificados se omiten")

    total_raw = len(df)
    if total_raw == 0:
        print("  No hay comentarios nuevos en TikTok DB")
        return pd.DataFrame(), "reglas"

    df["texto_limpio"] = df["message"].apply(limpiar_texto)
    df = df[df["texto_limpio"].notna()].copy()
    df["num_palabras"] = df["texto_limpio"].str.split().str.len()
    df = df[df["num_palabras"] >= 3].copy()
    print(f"  ({total_raw} comentarios nuevos → {len(df)} para análisis)")

    if df.empty:
        print("  Sin comentarios analizables en los comentarios nuevos")
        return pd.DataFrame(), "reglas"

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

    # Persistir el sentimiento por comentario (lo consume dash_fuente para TikTok).
    _persistir_sentimiento_comentarios_tiktok(db_path, df_res)

    total = len(df_res)
    for label in ["POS", "NEG", "NEU"]:
        pct = (df_res["label"] == label).sum() / total * 100
        print(f"    {label}: {pct:.1f}%")

    # D23: recalcular el agregado con TODOS los comentarios ya clasificados
    # del video (viejos + nuevos), no solo el lote nuevo de esta corrida.
    video_ids_afectados = sorted(set(df_res["video_id"]))
    placeholders = ",".join("?" for _ in video_ids_afectados)
    conn_full = sqlite3.connect(db_path)
    df_full = pd.read_sql_query(
        f"""
        SELECT id AS comment_id, video_id, text AS message, sentiment AS etiqueta_es,
               sentiment_score AS score_con_signo
        FROM comments
        WHERE video_id IN ({placeholders}) AND sentiment IS NOT NULL
        """,
        conn_full,
        params=video_ids_afectados,
    )
    conn_full.close()
    _map_inv = {"positivo": "POS", "negativo": "NEG", "neutral": "NEU"}
    df_full["label"] = df_full["etiqueta_es"].map(_map_inv).fillna("NEU")
    df_full["score"] = df_full["score_con_signo"].abs()

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

    agrupado = df_full.groupby("video_id").agg(
        total_comentarios=("comment_id", "count"),
        pct_positivo=("label", lambda x: (x == "POS").sum() / max(len(x), 1) * 100),
        pct_negativo=("label", lambda x: (x == "NEG").sum() / max(len(x), 1) * 100),
        pct_neutral=("label", lambda x: (x == "NEU").sum() / max(len(x), 1) * 100),
        comentario_mas_negativo=("video_id", lambda vid: _top_comment_by_neg(df_full[df_full["video_id"] == vid.iloc[0]])),
        comentario_mas_positivo=("video_id", lambda vid: _top_comment_by_pos(df_full[df_full["video_id"] == vid.iloc[0]])),
    ).reset_index()

    agrupado["score_sentimiento"] = agrupado["pct_positivo"] - agrupado["pct_negativo"]

    # D23: upsert real (delete + append) en vez de append puro.
    conn_up = sqlite3.connect(db_path)
    try:
        conn_up.execute(
            f"DELETE FROM tiktok_sentimiento WHERE video_id IN ({placeholders})",
            video_ids_afectados,
        )
    except sqlite3.OperationalError:
        pass
    agrupado.to_sql("tiktok_sentimiento", conn_up, if_exists="append", index=False)
    conn_up.commit()
    conn_up.close()

    print(f"  Videos actualizados (nuevos o con comentarios nuevos): {len(agrupado)}")
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
