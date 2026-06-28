"""Fuente unica de comentarios y sentimiento (verdad compartida).

Todos los bloques que hablan de comentarios, sentimiento, polarizacion o
fricciones deben usar ESTE modulo. Antes cada bloque cargaba los comentarios a
su manera: unos por publicacion, otros por comentario, unos del ultimo dia y
otros de toda la historia. Eso producia porcentajes que no coincidian entre si
("13/48/39" vs "38/28") y conteos parciales ("23 comentarios").

Reglas de la fuente unica:
  - Se cuenta el 100% de los comentarios del periodo, nunca una muestra.
  - El sentimiento se toma del propio comentario (fb_comments.sentiment /
    sentiment_score), no del promedio de la publicacion.
  - Un comentario sin sentimiento clasificable cuenta como NEUTRAL, de modo que
    favorable + neutral + critico siempre suma 100%.
  - El periodo se aplica por la fecha de la publicacion a la que pertenece el
    comentario (fb_comments no guarda fecha propia).
"""

import sqlite3

import pandas as pd

from config import FACEBOOK_DB

_POS = {"positivo", "muy_positivo", "positiva", "apoyo"}
_NEG = {"negativo", "muy_negativo", "negativa", "critica", "critico"}
_NEU = {"neutral", "neutro", "neutra"}


def cargar_comentarios_periodo(inicio, fin, db_path=None):
    """Devuelve TODOS los comentarios cuyo post cae en [inicio, fin].

    Columnas: comment_id, post_id, message, sentiment, sentiment_score,
    topic_category, zona, created_time.
    """
    db_path = db_path or FACEBOOK_DB
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            """
            SELECT fc.comment_id, fc.post_id, fc.message,
                   fc.sentiment, fc.sentiment_score, fc.topic_category, fc.zona,
                   fe.created_time
            FROM fb_comments fc
            LEFT JOIN fb_engagement fe ON fc.post_id = fe.post_id
            """,
            conn,
        )
    except Exception:
        return pd.DataFrame()
    finally:
        if conn is not None:
            conn.close()
    if df.empty:
        return df
    fechas = pd.to_datetime(df["created_time"], errors="coerce")
    mask = (fechas >= pd.Timestamp(inicio)) & (fechas <= pd.Timestamp(fin))
    return df[mask].copy()


def clasificar_comentario(row):
    """Etiqueta un comentario como favorable / neutral / critico.

    Prioriza la etiqueta textual del comentario; si no existe, usa el puntaje.
    Cualquier comentario sin dato utilizable cuenta como NEUTRAL.
    """
    s = str(row.get("sentiment") or "").strip().lower()
    if s in _POS:
        return "favorable"
    if s in _NEG:
        return "critico"
    if s in _NEU:
        return "neutral"
    try:
        sc = float(row.get("sentiment_score"))
    except (TypeError, ValueError):
        return "neutral"
    if sc > 0.1:
        return "favorable"
    if sc < -0.1:
        return "critico"
    return "neutral"


def distribucion_sentimiento(df):
    """Distribucion favorable/neutral/critico sobre el 100% de df."""
    n = 0 if df is None else len(df)
    base = {
        "n_total": n, "n_favorable": 0, "n_neutral": 0, "n_critico": 0,
        "pct_favorable": 0.0, "pct_neutral": 0.0, "pct_critico": 0.0,
    }
    if n == 0:
        return base
    etiquetas = df.apply(clasificar_comentario, axis=1)
    nf = int((etiquetas == "favorable").sum())
    nc = int((etiquetas == "critico").sum())
    nn = n - nf - nc
    base.update({
        "n_favorable": nf, "n_neutral": nn, "n_critico": nc,
        "pct_favorable": round(100 * nf / n, 1),
        "pct_neutral": round(100 * nn / n, 1),
        "pct_critico": round(100 * nc / n, 1),
    })
    return base


def frase_clima(dist):
    """Resumen en una frase del clima narrativo (lenguaje del alcalde)."""
    n = dist["n_total"]
    if n == 0:
        return "No hay comentarios en el periodo seleccionado."
    fav, neu, cri = dist["pct_favorable"], dist["pct_neutral"], dist["pct_critico"]
    if fav >= cri + 15:
        tono = "predominantemente favorable"
    elif cri >= fav + 15:
        tono = "predominantemente critica"
    elif abs(fav - cri) <= 10 and (fav + cri) > neu:
        tono = "dividida entre apoyo y critica"
    else:
        tono = "mayoritariamente neutral"
    return (
        f"De {n} comentarios analizados (el 100% del periodo), la conversacion "
        f"es {tono}: {fav:.0f}% a favor, {neu:.0f}% neutral y {cri:.0f}% "
        f"critica."
    )
