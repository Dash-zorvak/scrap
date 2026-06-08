import sqlite3
import pandas as pd
import os
import sys
sys.path.insert(0, "/Users/pro/Downloads/scrapeo-social/dashboard")
from config import *
import re
import unicodedata


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


POSITIVE_WORDS = {
    "buen", "buena", "bueno", "buenos", "buenas",
    "excelente", "excelentes", "genial", "geniales",
    "feliz", "felices", "felicidad", "gracias",
    "agradecido", "agradecida", "bien", "mejor", "mejores",
    "perfecto", "perfecta", "hermoso", "hermosa",
    "maravilloso", "maravillosa", "increible", "increibles",
    "fantastico", "fantastica", "apoyo", "apoyar",
    "adelante", "avance", "avances", "progreso",
    "trabajo", "trabajando", "logro", "logros",
    "exito", "exitosa", "exitoso",
    "beneficio", "beneficios", "orgullo", "orgulloso",
    "bonito", "bonita", "contento", "contenta",
    "alegria", "alegre", "gusta", "aprecio",
    "bendicion", "bendiciones", "seguridad", "seguro",
    "desarrollo", "crecimiento", "oportunidad",
    "transparencia", "honestidad", "eficiente",
    "victoria", "triunfo", "esperanza",
    "unidos", "unidad", "liderazgo",
    "magnifico", "espectacular", "brillante", "impresionante",
    "fenomenal", "estupendo",
}

NEGATIVE_WORDS = {
    "malo", "mala", "malos", "mal", "pesimo", "pesima",
    "horrible", "horribles",
    "triste", "tristes", "tristeza",
    "corrupto", "corrupta", "corrupcion",
    "fracaso", "fracasos", "peor", "peores",
    "deficiente", "incompetente", "mentira", "mentiras",
    "engano", "robo", "robos", "ladron", "ladrones",
    "inseguridad", "delincuencia", "violencia",
    "basura", "desastre", "verguenza", "vergonzoso",
    "odio", "detesto",
    "desempleo", "pobreza", "pobre", "pobres",
    "abandono", "abandonado", "incumplimiento",
    "falso", "falsa", "ineficiente",
    "crisis", "emergencia", "caos", "abusos",
    "injusticia", "injusto",
    "conflicto", "problema", "problemas",
    "grave", "graves", "preocupante",
    "deuda", "deudas", "aumento", "recorte",
    "lamentable", "deplorable", "desastroso",
    "intolerable", "insoportable", "nefasto",
}

NEGATION_WORDS = {"no", "nunca", "jamas", "tampoco", "ni"}


def _normalize(word):
    return unicodedata.normalize('NFKD', word).encode('ascii', 'ignore').decode('ascii')


def _match_word(word, stems):
    word = word.strip(".,!?;:¿¡\"'()").lower()
    word = _normalize(word)
    if not word or len(word) < 3:
        return False
    if word in stems:
        return True
    for s in [word[:-1], word.rstrip("s"), word.rstrip("aeo"),
               word.rstrip("os").rstrip("as")]:
        if len(s) >= 3 and s in stems:
            return True
    for suf in ("ado", "ido", "ada", "ida", "ando", "iendo",
                 "cion", "sion", "miento", "mente"):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            base = word[:-len(suf)]
            if base in stems:
                return True
            if base.rstrip("aeo") in stems:
                return True
    return False


def analizar_sentimiento_rapido(texto):
    if not texto:
        return ("NEU", 0.0)
    text_norm = _normalize(texto.lower())
    words = text_norm.split()

    positives = sum(1 for w in words if _match_word(w, POSITIVE_WORDS))
    negatives = sum(1 for w in words if _match_word(w, NEGATIVE_WORDS))

    for i, word in enumerate(words):
        wc = word.strip(".,!?;:¿¡\"'()")
        if wc in NEGATION_WORDS:
            for j in range(i + 1, min(i + 4, len(words))):
                nw = words[j].strip(".,!?;:¿¡\"'()")
                if _match_word(nw, POSITIVE_WORDS):
                    negatives += 1
                    positives = max(0, positives - 1)
                    break

    positives = max(0, positives)
    negatives = max(0, negatives)
    total = positives + negatives

    if total == 0:
        return ("NEU", 0.0)

    if positives > 0 and negatives == 0:
        return ("POS", round(min(positives / 5, 0.95), 4))
    elif negatives > 0 and positives == 0:
        return ("NEG", round(min(negatives / 5, 0.95), 4))

    ratio = positives / total
    if ratio >= 0.66:
        return ("POS", round(ratio, 4))
    elif ratio <= 0.33:
        return ("NEG", round(1 - ratio, 4))
    return ("NEU", round(ratio, 4))


def analizar_sentimiento_facebook():
    conn = sqlite3.connect(FACEBOOK_DB)
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
    for _, row in df.iterrows():
        label, score = analizar_sentimiento_rapido(row["texto_limpio"])
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
        return pd.DataFrame()

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

    conn = sqlite3.connect(FACEBOOK_DB)
    agrupado.to_sql("fb_sentimiento", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  Posts agrupados: {len(agrupado)}")
    return agrupado


def analizar_sentimiento_tiktok():
    conn = sqlite3.connect(TIKTOK_DB)
    df = pd.read_sql_query(
        "SELECT id as comment_id, video_id, text as message FROM comments WHERE text IS NOT NULL AND text != ''",
        conn,
    )
    conn.close()

    total_raw = len(df)
    if total_raw == 0:
        print("  No hay comentarios en TikTok DB")
        return pd.DataFrame()

    df["texto_limpio"] = df["message"].apply(limpiar_texto)
    df = df[df["texto_limpio"].notna()].copy()
    df["num_palabras"] = df["texto_limpio"].str.split().str.len()
    df = df[df["num_palabras"] >= 3].copy()
    print(f"  ({total_raw} comentarios crudos → {len(df)} para análisis)")

    resultados = []
    for _, row in df.iterrows():
        label, score = analizar_sentimiento_rapido(row["texto_limpio"])
        resultados.append({
            "comment_id": row["comment_id"],
            "video_id": row["video_id"],
            "message": row["message"],
            "label": label,
            "score": score,
        })

    if not resultados:
        print("  Sin resultados de sentimiento")
        return pd.DataFrame()

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

    conn = sqlite3.connect(TIKTOK_DB)
    agrupado.to_sql("tiktok_sentimiento", conn, if_exists="replace", index=False)
    conn.close()

    print(f"  Videos agrupados: {len(agrupado)}")
    return agrupado


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
    df_fb = analizar_sentimiento_facebook()
    print("▶ Analizando sentimiento TikTok...")
    df_tk = analizar_sentimiento_tiktok()
    imprimir_resultados(df_fb, df_tk)
    print("✓ Módulo 2 completo.")
