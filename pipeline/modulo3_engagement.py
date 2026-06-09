import logging
import sqlite3

import pandas as pd

from pipeline.config import PIPELINE_DB, OUTPUT_DIR, MIN_REACTIONS_FOR_RATIO
from pipeline.create_views import get_db, FB_POSTS_QUERY, TT_POSTS_QUERY

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def cargar_datos() -> tuple:
    conn = get_db()

    fb = pd.read_sql(f"""
        SELECT id, plataforma,
               me_gusta, me_encanta, me_divierte, me_asombra,
               me_entristece, me_enoja, comentarios_count, compartidos, views,
               (me_gusta+me_encanta+me_divierte+me_asombra+me_entristece+me_enoja) AS reacciones_totales
        FROM ({FB_POSTS_QUERY})
    """, conn)

    tt = pd.read_sql(f"""
        SELECT id, plataforma,
               me_gusta, 0 AS me_encanta, 0 AS me_divierte, 0 AS me_asombra,
               0 AS me_entristece, 0 AS me_enoja, comentarios_count, compartidos, views,
               me_gusta AS reacciones_totales
        FROM ({TT_POSTS_QUERY})
    """, conn)

    categorias = pd.read_sql("SELECT id, plataforma, etiqueta FROM post_categorias", conn)
    sentimiento = pd.read_sql("SELECT post_id, plataforma, score_sentimiento FROM post_sentimiento", conn)

    conn.close()

    df = pd.concat([fb, tt], ignore_index=True)
    df = df.merge(categorias, left_on=["id", "plataforma"], right_on=["id", "plataforma"], how="left")
    df = df.merge(sentimiento, left_on=["id", "plataforma"], right_on=["post_id", "plataforma"], how="left")

    log.info(f"Datos cargados: {len(df)} posts")
    return df


def calcular_metricas(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in df.iterrows():
        total_reacciones = int(row["reacciones_totales"])
        views = int(row["views"])
        compartidos = int(row["compartidos"])
        score_sent = row.get("score_sentimiento") or 0.0

        eng_total = total_reacciones + compartidos
        eng_rate = round(eng_total / views, 6) if views > 0 else 0.0

        # Emotional proxy indices
        if total_reacciones >= MIN_REACTIONS_FOR_RATIO:
            indice_afecto_positivo = (int(row["me_encanta"]) + int(row["me_asombra"])) / total_reacciones
            indice_controversia = (int(row["me_enoja"]) + int(row["me_entristece"])) / total_reacciones
            indice_humor = int(row["me_divierte"]) / total_reacciones
        else:
            indice_afecto_positivo = 0.0
            indice_controversia = 0.0
            indice_humor = 0.0

        indice_viralidad = round(compartidos / views, 6) if views > 0 else 0.0

        score_emocional_neto = round(
            indice_afecto_positivo - indice_controversia + (score_sent * 0.3), 4
        )

        results.append({
            "id": row["id"],
            "plataforma": row["plataforma"],
            "engagement_total": eng_total,
            "engagement_rate": eng_rate,
            "indice_afecto_positivo": round(indice_afecto_positivo, 4),
            "indice_controversia": round(indice_controversia, 4),
            "indice_humor": round(indice_humor, 4),
            "indice_viralidad": indice_viralidad,
            "score_emocional_neto": score_emocional_neto,
            "score_sentimiento": score_sent,
            "categoria": row.get("etiqueta", ""),
        })

    return pd.DataFrame(results)


def guardar_resultados(df: pd.DataFrame):
    conn = sqlite3.connect(PIPELINE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS post_engagement (
            id TEXT,
            plataforma TEXT,
            engagement_total INTEGER,
            engagement_rate REAL,
            indice_afecto_positivo REAL,
            indice_controversia REAL,
            indice_humor REAL,
            indice_viralidad REAL,
            score_emocional_neto REAL,
            score_sentimiento REAL,
            categoria TEXT
        )
    """)
    conn.execute("DELETE FROM post_engagement")
    df.to_sql("post_engagement", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

    csv_path = f"{OUTPUT_DIR}/post_engagement.csv"
    df.to_csv(csv_path, index=False)
    log.info(f"Resultados guardados: {len(df)} posts en post_engagement + CSV")


def run():
    log.info("=" * 50)
    log.info("MÓDULO 3 — Score de engagement emocional")
    log.info("=" * 50)

    df = cargar_datos()
    metricas = calcular_metricas(df)
    guardar_resultados(metricas)

    # Summary
    if not metricas.empty:
        log.info(f"  Engagement promedio: {metricas['engagement_total'].mean():.0f}")
        log.info(f"  Score emocional neto promedio: {metricas['score_emocional_neto'].mean():.4f}")
        log.info(f"  Índice de controversia promedio: {metricas['indice_controversia'].mean():.4f}")

    log.info("Módulo 3 completado.")
    return metricas


if __name__ == "__main__":
    run()
