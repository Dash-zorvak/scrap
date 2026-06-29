"""Fuente unica de comentarios y sentimiento (verdad compartida).

Todos los bloques que hablan de comentarios, sentimiento, polarizacion o
fricciones deben usar ESTE modulo. Antes cada bloque cargaba los comentarios a
su manera; eso producia porcentajes que no coincidian entre si y conteos
parciales.

Filtrado por plataforma
-----------------------
Cada comentario lleva una columna `plataforma` ("facebook" o "tiktok"). Las
funciones publicas reciben el filtro seleccionado en el panel ("Facebook",
"TikTok" o "Ambas") y SOLO cargan/combinan las fuentes que correspondan, de modo
que ninguna metrica mezcla plataformas cuando no debe:
  - Facebook  -> solo comentarios de Facebook (fb_comments + fb_sentimiento).
  - TikTok    -> solo comentarios de TikTok (comments + tiktok_sentimiento).
  - Ambas     -> se concatenan y la distribucion se combina ponderando por el
                 numero de comentarios de cada plataforma.

Reglas de la fuente unica (se mantienen por plataforma):
  - Se cuenta el 100% de los comentarios del periodo, nunca una muestra.
  - El sentimiento se toma de la tabla de sentimiento por publicacion/video
    (fb_sentimiento / tiktok_sentimiento), ponderado por la cantidad de
    comentarios. Si no hubiera datos, se cae a clasificar comentario por
    comentario.
  - favorable + neutral + critico siempre suma 100%.
  - El periodo se aplica por la fecha de la publicacion/video al que pertenece
    el comentario.
"""

import sqlite3

import pandas as pd

from config import FACEBOOK_DB, TIKTOK_DB

_POS = {
    "positivo", "muy_positivo", "positiva", "apoyo",
    "positive", "pos",
}
_NEG = {
    "negativo", "muy_negativo", "negativa", "critica", "critico",
    "negative", "neg",
}
_NEU = {"neutral", "neutro", "neutra", "mixto", "mixed"}

# Columnas canonicas que expone cualquier DataFrame de comentarios, sin importar
# la plataforma de origen. Garantiza que Facebook y TikTok se puedan concatenar
# sin desalinear columnas.
_COLUMNAS_COMENTARIOS = [
    "comment_id", "post_id", "message", "sentiment", "sentiment_score",
    "topic_category", "zona", "created_time", "plataforma",
]


def _norm_plataforma(plataforma):
    """Normaliza el selector de plataforma a 'facebook' | 'tiktok' | 'ambas'."""
    p = str(plataforma or "ambas").strip().lower()
    if p.startswith("face") or p == "fb":
        return "facebook"
    if p.startswith("tik") or p == "tk":
        return "tiktok"
    return "ambas"


def _cargar_comentarios_fb(inicio, fin, db_path=None):
    """Comentarios de Facebook cuyo post cae en [inicio, fin].

    La fecha del comentario se hereda de su publicacion: se prefiere
    fb_posts.created_time y, si falta, fb_engagement.created_time.
    """
    db_path = db_path or FACEBOOK_DB
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            """
            SELECT fc.comment_id, fc.post_id, fc.message,
                   fc.sentiment, fc.sentiment_score, fc.topic_category, fc.zona,
                   COALESCE(fp.created_time, fe.created_time) AS created_time
            FROM fb_comments fc
            LEFT JOIN fb_posts fp ON fc.post_id = fp.post_id
            LEFT JOIN fb_engagement fe ON fc.post_id = fe.post_id
            """,
            conn,
        )
    except Exception:
        return pd.DataFrame(columns=_COLUMNAS_COMENTARIOS)
    finally:
        if conn is not None:
            conn.close()
    if df.empty:
        return pd.DataFrame(columns=_COLUMNAS_COMENTARIOS)
    df["plataforma"] = "facebook"
    fechas = pd.to_datetime(df["created_time"], errors="coerce")
    mask = (fechas >= pd.Timestamp(inicio)) & (fechas <= pd.Timestamp(fin))
    return df[mask].copy()


def _cargar_comentarios_tk(inicio, fin, tk_db_path=None):
    """Comentarios de TikTok cuyo video cae en [inicio, fin].

    TikTok no guarda una fecha fiable por comentario, asi que la fecha se hereda
    del video (videos.created_at) y, si faltara, se usa comments.created_at. El
    sentimiento por comentario solo existe si modulo2 ya lo persistio en
    comments.sentiment / comments.sentiment_score; si no, queda NA y la
    distribucion se calcula desde tiktok_sentimiento.
    """
    tk_db_path = tk_db_path or TIKTOK_DB
    conn = None
    try:
        conn = sqlite3.connect(tk_db_path)
        cdf = pd.read_sql("SELECT * FROM comments", conn)
        vdf = pd.read_sql("SELECT id, created_at FROM videos", conn)
    except Exception:
        return pd.DataFrame(columns=_COLUMNAS_COMENTARIOS)
    finally:
        if conn is not None:
            conn.close()
    if cdf is None or cdf.empty:
        return pd.DataFrame(columns=_COLUMNAS_COMENTARIOS)

    cdf = cdf.reset_index(drop=True)
    out = pd.DataFrame(index=cdf.index)
    out["comment_id"] = cdf["id"] if "id" in cdf.columns else pd.NA
    out["post_id"] = cdf["video_id"].astype(str) if "video_id" in cdf.columns else pd.NA
    out["message"] = cdf["text"] if "text" in cdf.columns else pd.NA
    out["sentiment"] = cdf["sentiment"] if "sentiment" in cdf.columns else pd.NA
    out["sentiment_score"] = cdf["sentiment_score"] if "sentiment_score" in cdf.columns else pd.NA
    out["topic_category"] = cdf["topic_category"] if "topic_category" in cdf.columns else pd.NA
    out["zona"] = cdf["zona"] if "zona" in cdf.columns else pd.NA

    fecha_video = {}
    if vdf is not None and not vdf.empty:
        v = vdf.copy()
        v["id"] = v["id"].astype(str)
        fecha_video = dict(zip(v["id"], v["created_at"]))
    created = out["post_id"].astype(str).map(fecha_video)
    if "created_at" in cdf.columns:
        created = created.fillna(cdf["created_at"])
    out["created_time"] = created
    out["plataforma"] = "tiktok"
    out = out[_COLUMNAS_COMENTARIOS]

    fechas = pd.to_datetime(out["created_time"], errors="coerce")
    mask = (fechas >= pd.Timestamp(inicio)) & (fechas <= pd.Timestamp(fin))
    return out[mask].copy()


def cargar_comentarios_periodo(inicio, fin, plataforma="Ambas", db_path=None, tk_db_path=None):
    """Devuelve TODOS los comentarios del periodo segun la plataforma elegida.

    Columnas: comment_id, post_id, message, sentiment, sentiment_score,
    topic_category, zona, created_time, plataforma.
    """
    plat = _norm_plataforma(plataforma)
    partes = []
    if plat in ("facebook", "ambas"):
        partes.append(_cargar_comentarios_fb(inicio, fin, db_path))
    if plat in ("tiktok", "ambas"):
        partes.append(_cargar_comentarios_tk(inicio, fin, tk_db_path))
    partes = [p for p in partes if p is not None and not p.empty]
    if not partes:
        return pd.DataFrame(columns=_COLUMNAS_COMENTARIOS)
    return pd.concat(partes, ignore_index=True)


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


def _dist_por_comentario(df, n):
    """Respaldo: distribucion contando la etiqueta de cada comentario."""
    etiquetas = df.apply(clasificar_comentario, axis=1)
    nf = int((etiquetas == "favorable").sum())
    nc = int((etiquetas == "critico").sum())
    nn = n - nf - nc
    return (
        round(100 * nf / n, 1),
        round(100 * nn / n, 1),
        round(100 * nc / n, 1),
    )


def _ponderar_pcts(sdf):
    """(fav, neu, cri) ponderando pct_positivo/pct_negativo por total_comentarios.

    Es la misma logica para Facebook y TikTok: cada tabla de sentimiento por
    publicacion/video trae pct_positivo, pct_negativo y total_comentarios.
    """
    if sdf is None or sdf.empty:
        return None
    sdf = sdf.reset_index(drop=True)
    peso = pd.to_numeric(sdf["total_comentarios"], errors="coerce").fillna(0)
    peso = peso.clip(lower=0)
    total = peso.sum()
    if total <= 0:
        peso = pd.Series([1.0] * len(sdf))
        total = peso.sum()
    pos = pd.to_numeric(sdf["pct_positivo"], errors="coerce").fillna(0)
    neg = pd.to_numeric(sdf["pct_negativo"], errors="coerce").fillna(0)
    fav = float((pos * peso).sum() / total)
    cri = float((neg * peso).sum() / total)
    neu = max(0.0, 100.0 - fav - cri)
    return round(fav, 1), round(neu,