import logging
import sqlite3

import pandas as pd

from pipeline.config import PIPELINE_DB, OUTPUT_DIR, SENTIMENT_MIN_TEXT_LENGTH
from pipeline.create_views import get_db, FB_COMMENTS_QUERY, TT_COMMENTS_QUERY

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

HAS_PYSENTIMIENTO = False
SA = None
log.info("Usando clasificador rule-based (rápido). Para pysentimiento, cambiar HAS_PYSENTIMIENTO manualmente.")

POS_WORDS = {
    "excelente", "maravilloso", "felicidades", "gracias", "bendiciones",
    "apoyo", "orgullo", "hermoso", "genial", "increíble", "fantástico",
    "buen trabajo", "bien hecho", "adelante", "éxito", "progreso",
    "me gusta", "super", "bravo", "espectacular", "perfecto",
}
NEG_WORDS = {
    "corrupto", "mentiroso", "fracaso", "verguenza", "pésimo", "horrible",
    "terrible", "incompetente", "ladrón", "delincuente", "basura",
    "asqueroso", "pobre", "malo", "peor", "decepcionante",
    "no sirve", "dimisión", "renuncie", "vergüenza", "ratas",
}


def clasificar_texto(texto: str) -> tuple:
    if not texto or len(texto.strip()) < SENTIMENT_MIN_TEXT_LENGTH:
        return ("neutral", 0.0)

    text_lower = texto.lower().strip()
    words = set(text_lower.split())
    pos_count = len(words & POS_WORDS)
    neg_count = len(words & NEG_WORDS)
    if pos_count > neg_count:
        return ("positivo", min(1.0, pos_count * 0.25))
    if neg_count > pos_count:
        return ("negativo", min(1.0, neg_count * 0.25))
    return ("neutral", 0.0)


def cargar_comentarios() -> pd.DataFrame:
    conn = get_db()

    fb = pd.read_sql(f"SELECT post_id, texto, plataforma FROM ({FB_COMMENTS_QUERY})", conn)
    tt = pd.read_sql(f"SELECT post_id, texto, plataforma FROM ({TT_COMMENTS_QUERY})", conn)
    conn.close()
    df = pd.concat([fb, tt], ignore_index=True)
    log.info(f"Comentarios cargados: {len(df)} (FB: {len(fb)}, TT: {len(tt)})")
    return df


def clasificar_comentarios(df: pd.DataFrame) -> pd.DataFrame:
    resultados = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        sent, score = clasificar_texto(row["texto"])
        resultados.append({
            "post_id": row["post_id"],
            "plataforma": row["plataforma"],
            "sentimiento": sent,
            "score": score,
        })
        if (i + 1) % 500 == 0:
            log.info(f"  Clasificados {i+1}/{total}")
    return pd.DataFrame(resultados)


def agregar_por_post(df_clasif: pd.DataFrame) -> pd.DataFrame:
    grouped = df_clasif.groupby(["post_id", "plataforma"])
    rows = []
    for (pid, plat), group in grouped:
        total = len(group)
        if total < 3:
            continue
        counts = group["sentimiento"].value_counts()
        pct_pos = counts.get("positivo", 0) / total * 100
        pct_neg = counts.get("negativo", 0) / total * 100
        pct_neu = counts.get("neutral", 0) / total * 100
        score = (pct_pos - pct_neg) / 100.0
        rows.append({
            "post_id": pid,
            "plataforma": plat,
            "total_comentarios": total,
            "pct_positivo": round(pct_pos, 1),
            "pct_negativo": round(pct_neg, 1),
            "pct_neutral": round(pct_neu, 1),
            "score_sentimiento": round(score, 3),
        })
    return pd.DataFrame(rows)


def guardar_resultados(agregado: pd.DataFrame):
    conn = sqlite3.connect(PIPELINE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS post_sentimiento (
            post_id TEXT,
            plataforma TEXT,
            total_comentarios INTEGER,
            pct_positivo REAL,
            pct_negativo REAL,
            pct_neutral REAL,
            score_sentimiento REAL
        )
    """)
    conn.execute("DELETE FROM post_sentimiento")
    agregado.to_sql("post_sentimiento", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

    csv_path = f"{OUTPUT_DIR}/post_sentimiento.csv"
    agregado.to_csv(csv_path, index=False)
    log.info(f"Resultados guardados: {len(agregado)} posts en post_sentimiento + CSV")


def run():
    log.info("=" * 50)
    log.info("MÓDULO 2 — Análisis de sentimiento en comentarios")
    log.info("=" * 50)

    df = cargar_comentarios()
    clasif = clasificar_comentarios(df)
    agregado = agregar_por_post(clasif)
    guardar_resultados(agregado)
    log.info("Módulo 2 completado.")
    return agregado


if __name__ == "__main__":
    run()
