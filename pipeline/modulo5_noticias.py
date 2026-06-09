import logging
import sqlite3
from datetime import datetime, timedelta

import pandas as pd

from pipeline.config import PIPELINE_DB, OUTPUT_DIR
from pipeline.create_views import get_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def cargar_anomalias() -> pd.DataFrame:
    conn = sqlite3.connect(PIPELINE_DB)
    try:
        anomalias = pd.read_sql("""
            SELECT periodo, plataforma, semana_label, total_posts,
                   engagement_total, engagement_promedio, tipo_anomalia
            FROM series_temporales
            WHERE es_anomalia = 1
        """, conn)
    except Exception as e:
        log.warning(f"No se pudieron cargar anomalías: {e}")
        anomalias = pd.DataFrame()
    conn.close()
    log.info(f"Anomalías cargadas: {len(anomalias)}")
    return anomalias


def clasificar_noticia(texto: str) -> tuple:
    text_lower = texto.lower()
    if any(w in text_lower for w in ["positivo", "logro", "avance", "beneficio", "éxito", "mejora", "inauguración"]):
        return ("positiva", "logro")
    if any(w in text_lower for w in ["denuncia", "corrupción", "problema", "crisis", "queja", "conflicto", "violencia"]):
        return ("negativa", "problema")
    return ("neutral", "general")


def generar_eventos_simulados() -> pd.DataFrame:
    events = [
        {
            "fecha": "2025-05-15",
            "titular": "Inauguración de parque en Santa Ana Centro",
            "fuente": "La Prensa Gráfica",
            "url": "https://example.com/noticia1",
        },
        {
            "fecha": "2025-06-01",
            "titular": "Denuncias por calles dañadas en colonia Santa Lucía",
            "fuente": "El Diario de Hoy",
            "url": "https://example.com/noticia2",
        },
        {
            "fecha": "2025-07-20",
            "titular": "Alcaldía lanza programa de becas municipales",
            "fuente": "La Prensa Gráfica",
            "url": "https://example.com/noticia3",
        },
    ]
    df = pd.DataFrame(events)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df[["clasificacion", "tema"]] = df["titular"].apply(lambda x: pd.Series(clasificar_noticia(x)))
    return df


def correlacionar(anomalias: pd.DataFrame, noticias: pd.DataFrame) -> pd.DataFrame:
    if anomalias.empty or noticias.empty:
        log.warning("Datos insuficientes para correlación")
        return pd.DataFrame()

    anomalias["periodo_dt"] = pd.to_datetime(anomalias["semana_label"], errors="coerce")

    results = []
    for _, noticia in noticias.iterrows():
        fecha_n = noticia["fecha"]
        window_start = fecha_n - timedelta(days=3)
        window_end = fecha_n + timedelta(days=3)

        cercanas = anomalias[
            (anomalias["periodo_dt"] >= window_start) &
            (anomalias["periodo_dt"] <= window_end)
        ]

        for _, anom in cercanas.iterrows():
            results.append({
                "noticia_titular": noticia["titular"],
                "noticia_fuente": noticia["fuente"],
                "noticia_fecha": fecha_n.strftime("%Y-%m-%d"),
                "noticia_clasificacion": noticia.get("clasificacion", ""),
                "anomalia_periodo": anom["periodo"],
                "anomalia_plataforma": anom["plataforma"],
                "anomalia_tipo": anom["tipo_anomalia"],
                "anomalia_engagement": anom["engagement_total"],
                "dias_diferencia": abs((fecha_n - anom["periodo_dt"]).days),
            })

    return pd.DataFrame(results)


def guardar_resultados(correlacion: pd.DataFrame, noticias: pd.DataFrame):
    conn = sqlite3.connect(PIPELINE_DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS noticias_externas (
            noticia_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            titular TEXT,
            texto TEXT,
            fuente TEXT,
            url TEXT,
            clasificacion TEXT,
            tema TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS eventos_correlacionados (
            noticia_titular TEXT,
            noticia_fuente TEXT,
            noticia_fecha TEXT,
            noticia_clasificacion TEXT,
            anomalia_periodo TEXT,
            anomalia_plataforma TEXT,
            anomalia_tipo TEXT,
            anomalia_engagement INTEGER,
            dias_diferencia INTEGER
        )
    """)

    conn.execute("DELETE FROM noticias_externas")
    conn.execute("DELETE FROM eventos_correlacionados")

    for _, row in noticias.iterrows():
        conn.execute(
            "INSERT INTO noticias_externas (fecha, titular, fuente, url, clasificacion, tema) VALUES (?,?,?,?,?,?)",
            (row["fecha"].strftime("%Y-%m-%d"), row["titular"], row.get("fuente", ""),
             row.get("url", ""), row.get("clasificacion", ""), row.get("tema", "")),
        )

    if not correlacion.empty:
        correlacion.to_sql("eventos_correlacionados", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()

    noticias.to_csv(f"{OUTPUT_DIR}/noticias_externas.csv", index=False)
    if not correlacion.empty:
        correlacion.to_csv(f"{OUTPUT_DIR}/eventos_correlacionados.csv", index=False)
    log.info(f"Noticias: {len(noticias)} · Correlaciones: {len(correlacion)}")


def run():
    log.info("=" * 50)
    log.info("MÓDULO 5 — Contexto externo (noticias)")
    log.info("=" * 50)

    anomalias = cargar_anomalias()
    noticias = generar_eventos_simulados()
    correlacion = correlacionar(anomalias, noticias)
    guardar_resultados(correlacion, noticias)

    if not correlacion.empty:
        log.info(f"  {len(correlacion)} correlaciones noticia ↔ pico de engagement")
        for _, r in correlacion.iterrows():
            log.info(f"    {r['noticia_titular'][:40]} ↔ {r['anomalia_tipo']} ({r['dias_diferencia']}d)")

    log.info("Módulo 5 completado.")
    return correlacion


if __name__ == "__main__":
    run()
