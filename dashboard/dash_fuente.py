"""Fuente unica de comentarios y sentimiento (verdad compartida).

Todos los bloques que hablan de comentarios, sentimiento, polarizacion o
fricciones deben usar ESTE modulo.

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

import os
import sqlite3
import sys
import logging

import pandas as pd
import streamlit as st

# Permite importar este modulo de forma aislada (p.ej. en tests) sin depender de
# que app.py haya configurado antes el sys.path. config.py vive en este mismo
# directorio (dashboard/); ademas anadimos la raiz del repo para el paquete
# `dashboard`. Mismo bootstrap que usan editor_db.py y medalla_dashboard.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FACEBOOK_DB, TIKTOK_DB  # noqa: E402
from dashboard.dash_periodos import filtrar_por_fecha  # noqa: E402

logger = logging.getLogger("dash_fuente")

try:
    from dashboard.config import FACEBOOK_DB as DASH_FACEBOOK_DB  # noqa: E402
except Exception:
    DASH_FACEBOOK_DB = FACEBOOK_DB

_POS = {
    "positivo", "muy_positivo", "positiva", "apoyo",
    "positive", "pos",
}
_NEG = {
    "negativo", "muy_negativo", "negativa", "critica", "critico",
    "negative", "neg",
}
_NEU = {"neutral", "neutro", "neutra", "mixto", "mixed"}

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

    Desacoplado del esquema heredado: selecciona fc.* y rellena con NA las
    columnas OPCIONALES (sentiment, sentiment_score, topic_category, zona) que
    pudieran no existir, exactamente igual que _cargar_comentarios_tk. Asi, al
    podar columnas heredadas como `zona` o `topic_category`, los comentarios de
    Facebook siguen apareciendo en el dashboard en vez de desaparecer por una
    excepcion de SQL.
    """
    db_path = db_path or FACEBOOK_DB
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cdf = pd.read_sql("SELECT * FROM fb_comments", conn)
        try:
            jdf = pd.read_sql("SELECT post_id, created_time FROM fb_posts", conn)
        except Exception as e:
            logger.warning("No se pudo leer fb_posts para join de fechas: %s", e)
            jdf = None
        try:
            edf = pd.read_sql("SELECT post_id, created_time FROM fb_engagement", conn)
        except Exception as e:
            logger.warning("No se pudo leer fb_engagement para join de fechas: %s", e)
            edf = None
    except Exception as e:
        logger.exception("Fallo leyendo fb_comments para _cargar_comentarios_fb")
        try:
            st.warning("No se pudieron cargar los comentarios de Facebook de este período (error interno). Los números pueden estar incompletos.")
        except Exception:
            pass
        return pd.DataFrame(columns=_COLUMNAS_COMENTARIOS)
    finally:
        if conn is not None:
            conn.close()
    if cdf is None or cdf.empty:
        return pd.DataFrame(columns=_COLUMNAS_COMENTARIOS)

    cdf = cdf.reset_index(drop=True)
    out = pd.DataFrame(index=cdf.index)
    out["comment_id"] = cdf["comment_id"] if "comment_id" in cdf.columns else pd.NA
    out["post_id"] = cdf["post_id"].astype(str) if "post_id" in cdf.columns else pd.NA
    out["message"] = cdf["message"] if "message" in cdf.columns else pd.NA
    out["sentiment"] = cdf["sentiment"] if "sentiment" in cdf.columns else pd.NA
    out["sentiment_score"] = cdf["sentiment_score"] if "sentiment_score" in cdf.columns else pd.NA
    out["topic_category"] = cdf["topic_category"] if "topic_category" in cdf.columns else pd.NA
    out["zona"] = cdf["zona"] if "zona" in cdf.columns else pd.NA

    # Fecha heredada del post (fb_posts), con respaldo en fb_engagement.
    fecha_post = {}
    if jdf is not None and not jdf.empty:
        j = jdf.copy()
        j["post_id"] = j["post_id"].astype(str)
        fecha_post = dict(zip(j["post_id"], j["created_time"]))
    fecha_eng = {}
    if edf is not None and not edf.empty:
        e = edf.copy()
        e["post_id"] = e["post_id"].astype(str)
        fecha_eng = dict(zip(e["post_id"], e["created_time"]))
    created = out["post_id"].astype(str).map(fecha_post)
    created = created.fillna(out["post_id"].astype(str).map(fecha_eng))
    out["created_time"] = created
    out["plataforma"] = "facebook"
    out = out[_COLUMNAS_COMENTARIOS]

    fechas = pd.to_datetime(out["created_time"], errors="coerce")
    mask = (fechas >= pd.Timestamp(inicio)) & (fechas <= pd.Timestamp(fin))
    return out[mask].copy()


def _cargar_comentarios_tk(inicio, fin, tk_db_path=None):
    """Comentarios de TikTok cuyo video cae en [inicio, fin].

    TikTok no guarda una fecha fiable por comentario: la fecha se hereda del
    video (videos.created_at) y, si faltara, se usa comments.created_at. El
    sentimiento por comentario solo existe si modulo2 ya lo persisto en
    comments.sentiment / comments.sentiment_score; si no, queda NA y la
    distribucion se calcula desde tiktok_sentimiento.
    """
    tk_db_path = tk_db_path or TIKTOK_DB
    conn = None
    try:
        conn = sqlite3.connect(tk_db_path)
        cdf = pd.read_sql("SELECT * FROM comments", conn)
        vdf = pd.read_sql("SELECT id, created_at FROM videos", conn)
    except Exception as e:
        logger.exception("Fallo leyendo comments/videos de TikTok para _cargar_comentarios_tk")
        try:
            st.warning("No se pudieron cargar los comentarios de TikTok de este período (error interno). Los números pueden estar incompletos.")
        except Exception:
            pass
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
    """Devuelve TODOS los comentarios del periodo segun la plataforma elegida."""
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


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_engagement_periodo(ini, fin, plataforma="Ambas", fb_db=None, tk_db=None):
    """Carga engagement + sentimiento + categorias de FB y TK filtrados por plataforma y fecha.

    Facebook: fb_engagement LEFT JOIN post_categorias LEFT JOIN fb_sentimiento
    TikTok:   tiktok_engagement LEFT JOIN post_categorias LEFT JOIN tiktok_sentimiento

    Devuelve (df_fb, df_tk) con las columnas necesarias para todos los bloques.
    El filtro de fecha usa EXCLUSIVAMENTE dash_periodos.filtrar_por_fecha.
    ini=None, fin=None => sin filtro de período (solo plataforma).
    """
    from config import FACEBOOK_DB as _FACEBOOK_DB, TIKTOK_DB as _TIKTOK_DB
    fb_db = fb_db or _FACEBOOK_DB
    tk_db = tk_db or _TIKTOK_DB
    plat = _norm_plataforma(plataforma)

    df_fb = pd.DataFrame()
    df_tk = pd.DataFrame()

    if plat in ("facebook", "ambas"):
        try:
            conn = sqlite3.connect(fb_db)
            df_fb = pd.read_sql("""
                SELECT fe.*, pc.categoria_nombre,
                       fs.score_sentimiento, fs.pct_positivo, fs.pct_negativo,
                       fs.total_comentarios as sent_total_comentarios
                FROM fb_engagement fe
                LEFT JOIN post_categorias pc ON fe.post_id = pc.item_id
                LEFT JOIN fb_sentimiento fs ON fe.post_id = fs.post_id
            """, conn)
            conn.close()
            if not df_fb.empty:
                df_fb["created_time"] = pd.to_datetime(df_fb["created_time"], errors="coerce")
                if ini is not None and fin is not None:
                    df_fb = filtrar_por_fecha(df_fb, "created_time", ini, fin)
                df_fb = df_fb.dropna(subset=["created_time"])
        except Exception:
            df_fb = pd.DataFrame()

    if plat in ("tiktok", "ambas"):
        try:
            conn = sqlite3.connect(tk_db)
            df_tk = pd.read_sql("SELECT * FROM tiktok_engagement", conn)
            # Categorías (post_categorias puede no existir en todas las BDs)
            try:
                cats = pd.read_sql("SELECT item_id, categoria_nombre FROM post_categorias", conn)
                if not cats.empty:
                    cats["item_id"] = cats["item_id"].astype(str)
                    df_tk["id_str"] = df_tk["id"].astype(str)
                    df_tk = df_tk.merge(cats, left_on="id_str", right_on="item_id", how="left")
                    df_tk = df_tk.drop(columns=["id_str", "item_id"], errors="ignore")
            except Exception:
                df_tk["categoria_nombre"] = pd.Series(dtype=str)
            # Sentimiento
            try:
                sent = pd.read_sql("SELECT video_id, pct_positivo, pct_negativo, total_comentarios FROM tiktok_sentimiento", conn)
                if not sent.empty:
                    sent["video_id"] = sent["video_id"].astype(str)
                    df_tk["id_str"] = df_tk["id"].astype(str)
                    df_tk = df_tk.merge(sent, left_on="id_str", right_on="video_id", how="left")
                    df_tk = df_tk.drop(columns=["id_str", "video_id"], errors="ignore")
            except Exception:
                pass
            conn.close()
            if not df_tk.empty:
                df_tk["created_at"] = pd.to_datetime(df_tk["created_at"], errors="coerce")
                if ini is not None and fin is not None:
                    df_tk = filtrar_por_fecha(df_tk, "created_at", ini, fin)
                df_tk = df_tk.dropna(subset=["created_at"])
        except Exception:
            df_tk = pd.DataFrame()

    return df_fb, df_tk


def clasificar_comentario(row):
    """Etiqueta un comentario como favorable / neutral / critico.

    Usa pd.isna() para tratar los nulos de pandas (pd.NA) de forma segura: con
    columnas opcionales rellenadas con pd.NA, `row.get("sentiment") or ""`
    invocaba bool(pd.NA) —cuyo valor de verdad es ambiguo— y reventaba el apply
    con "boolean value of NA is ambiguous".
    """
    raw = row.get("sentiment")
    s = "" if raw is None or pd.isna(raw) else str(raw)
    s = s.strip().lower()
    if s in _POS:
        return "favorable"
    if s in _NEG:
        return "critico"
    if s in _NEU:
        return "neutral"
    raw_score = row.get("sentiment_score")
    if raw_score is None or pd.isna(raw_score):
        return "neutral"
    try:
        sc = float(raw_score)
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
    """(fav, neu, cri) ponderando pct_positivo/pct_negativo por total_comentarios."""
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
    return round(fav, 1), round(neu, 1), round(cri, 1)


def _dist_desde_fb_sentimiento(post_ids, db_path):
    if not post_ids:
        return None
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        marcadores = ",".join(["?"] * len(post_ids))
        sdf = pd.read_sql(
            "SELECT post_id, pct_positivo, pct_negativo, total_comentarios "
            f"FROM fb_sentimiento WHERE post_id IN ({marcadores})",
            conn,
            params=list(post_ids),
        )
    except Exception as e:
        logger.exception("Fallo leyendo fb_sentimiento para _dist_desde_fb_sentimiento")
        try:
            st.warning("No se pudo calcular el sentimiento agregado de Facebook para este período; se usará una estimación por comentario.")
        except Exception:
            pass
        return None
    finally:
        if conn is not None:
            conn.close()
    return _ponderar_pcts(sdf)


def _dist_desde_tiktok_sentimiento(video_ids, tk_db_path):
    if not video_ids:
        return None
    conn = None
    try:
        conn = sqlite3.connect(tk_db_path)
        marcadores = ",".join(["?"] * len(video_ids))
        sdf = pd.read_sql(
            "SELECT video_id, pct_positivo, pct_negativo, total_comentarios "
            f"FROM tiktok_sentimiento WHERE video_id IN ({marcadores})",
            conn,
            params=[str(v) for v in video_ids],
        )
    except Exception as e:
        logger.exception("Fallo leyendo tiktok_sentimiento para _dist_desde_tiktok_sentimiento")
        try:
            st.warning("No se pudo calcular el sentimiento agregado de TikTok para este período; se usará una estimación por comentario.")
        except Exception:
            pass
        return None
    finally:
        if conn is not None:
            conn.close()
    return _ponderar_pcts(sdf)


def _dist_subset(df_sub, plat_key, db_path, tk_db_path):
    """(fav, neu, cri) de un subconjunto homogeneo de UNA plataforma."""
    n = 0 if df_sub is None else len(df_sub)
    if n == 0:
        return None
    pcts = None
    if "post_id" in df_sub.columns:
        ids = [p for p in df_sub["post_id"].dropna().unique().tolist()]
        if plat_key == "tiktok":
            pcts = _dist_desde_tiktok_sentimiento(ids, tk_db_path or TIKTOK_DB)
        else:
            pcts = _dist_desde_fb_sentimiento(ids, db_path or FACEBOOK_DB)
    if pcts is None:
        pcts = _dist_por_comentario(df_sub, n)
    return pcts


def distribucion_sentimiento(df, plataforma="Ambas", db_path=None, tk_db_path=None):
    """Distribucion favorable/neutral/critico sobre el 100% de df.

    Si df trae la columna `plataforma`, se calcula la distribucion de cada
    plataforma con su propia fuente de sentimiento y se combinan ponderando por
    el numero de comentarios de cada una. Asi una metrica "Ambas" nunca usa la
    tabla equivocada para una fila.
    """
    n = 0 if df is None else len(df)
    base = {
        "n_total": n, "n_favorable": 0, "n_neutral": 0, "n_critico": 0,
        "pct_favorable": 0.0, "pct_neutral": 0.0, "pct_critico": 0.0,
    }
    if n == 0:
        return base
    db_path = db_path or FACEBOOK_DB
    tk_db_path = tk_db_path or TIKTOK_DB

    if "plataforma" in df.columns:
        grupos = []
        for plat_key, sub in df.groupby("plataforma"):
            pcts = _dist_subset(sub, str(plat_key).strip().lower(), db_path, tk_db_path)
            if pcts is not None:
                grupos.append((len(sub), pcts))
        if grupos:
            peso_total = sum(w for w, _ in grupos)
            pf = sum(w * p[0] for w, p in grupos) / peso_total
            pn = sum(w * p[1] for w, p in grupos) / peso_total
            pc = sum(w * p[2] for w, p in grupos) / peso_total
        else:
            pf, pn, pc = _dist_por_comentario(df, n)
    else:
        pcts = _dist_subset(df, _norm_plataforma(plataforma), db_path, tk_db_path)
        if pcts is None:
            pcts = _dist_por_comentario(df, n)
        pf, pn, pc = pcts

    pf = round(pf, 1)
    pn = round(pn, 1)
    pc = round(pc, 1)
    nf = int(round(n * pf / 100))
    nc = int(round(n * pc / 100))
    nn = max(0, n - nf - nc)
    base.update({
        "n_favorable": nf, "n_neutral": nn, "n_critico": nc,
        "pct_favorable": pf, "pct_neutral": pn, "pct_critico": pc,
    })
    return base


def frase_clima(dist):
    """Frase corta que resume el clima narrativo a partir de la distribucion."""
    fav = dist.get("pct_favorable", 0)
    cri = dist.get("pct_critico", 0)
    if dist.get("n_total", 0) == 0:
        return "Sin comentarios en el periodo"
    if cri >= 50:
        return "Clima predominantemente critico"
    if fav >= 50:
        return "Clima predominantemente favorable"
    if cri > fav:
        return "Clima mixto con tendencia critica"
    if fav > cri:
        return "Clima mixto con tendencia favorable"
    return "Clima equilibrado"


def mapa_categoria_posts(db_path=None):
    """{post_id(str): categoria_nombre(str)} desde post_categorias (FB).

    El tema de cada comentario se toma de la categoría de SU publicación, porque
    fb_comments.topic_category casi nunca está poblado (el pipeline clasifica
    POSTS en post_categorias, no comentarios). Devuelve {} si no hay tabla/datos.
    """
    db_path = db_path or DASH_FACEBOOK_DB
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            "SELECT item_id, categoria_nombre FROM post_categorias "
            "WHERE categoria_nombre IS NOT NULL AND TRIM(categoria_nombre) != ''",
            conn,
        )
        conn.close()
        if df is None or df.empty:
            return {}
        return {str(i): str(c) for i, c in zip(df["item_id"], df["categoria_nombre"])}
    except Exception as e:
        logger.exception("Fallo leyendo post_categorias para mapa_categoria_posts")
        try:
            st.warning("No se pudo cargar la categoría de las publicaciones; los temas pueden aparecer sin agrupar.")
        except Exception:
            pass
        return {}


def tema_por_comentario(df, db_path=None):
    """Serie con el tema de cada comentario: categoría de su post
    (post_categorias), con respaldo en topic_category del comentario; '' si no
    hay ninguno.
    """
    if df is None or df.empty:
        return pd.Series(dtype=str)
    cat_por_post = mapa_categoria_posts(db_path)

    def _t(row):
        pid = str(row.get("post_id") or "")
        cat = cat_por_post.get(pid)
        if cat and str(cat).strip():
            return str(cat)
        tc = row.get("topic_category")
        if tc is not None and not pd.isna(tc) and str(tc).strip():
            return str(tc)
        return ""

    return df.apply(_t, axis=1)
