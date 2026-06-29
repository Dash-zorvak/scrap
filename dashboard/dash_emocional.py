"""Modelo emocional por plataforma (score emocional e indice de enojo).

DECISION TECNICA - por que NO se reutiliza el algoritmo de Facebook en TikTok
============================================================================
Facebook expone SEIS reacciones afectivas tipadas por publicacion (me gusta,
me encanta, me importa, me asombra, me entristece y me enoja). De ahi se derivan
de forma NATIVA:
  - score_emocional: balance afectivo (afecto positivo - afecto negativo)
  - indice_enojo:    proporcion de la reaccion "me enoja" sobre el total
Ese modelo tiene sentido porque cada reaccion es una senal emocional EXPLICITA
emitida por el usuario.

TikTok NO ofrece reacciones tipadas: solo likes, comentarios, compartidos,
favoritos y visualizaciones, que son senales de ALCANCE/INTERES, no de emocion.
Copiar el modelo de Facebook (p. ej. tratar "favoritos" como "me encanta" o
derivar enojo de "compartidos") seria estadisticamente arbitrario y
conceptualmente incorrecto: en TikTok no existe la senal "me enoja".

La UNICA senal afectiva real disponible en TikTok es el SENTIMIENTO DE LOS
COMENTARIOS (tabla tiktok_sentimiento: pct_positivo / pct_negativo por video).
Por eso TikTok usa un modelo PROPIO basado en el sentimiento de comentarios:
  - indice_enojo    = proporcion de comentarios negativos        -> pct_negativo / 100        en [0, 1]
  - score_emocional = balance neto del sentimiento de comentarios -> (pct_pos - pct_neg) / 100 en [-1, 1]

Ambos quedan en la MISMA escala que sus equivalentes de Facebook
(score_emocional ~[-1, 1], indice_enojo ~[0, 1]), de modo que la combinacion
"Ambas" es coherente. La combinacion pondera cada plataforma por su VOLUMEN
(total_reacciones en FB, total_comentarios en TikTok), que es la unidad de
"masa emocional" comparable entre ambas.

Arquitectura: cada plataforma implementa su propio calculo
(emocional_facebook / emocional_tiktok) y `metricas_emocionales` las orquesta.
Anadir una red nueva = escribir una funcion emocional_<red>() y registrarla
aqui, sin tocar los bloques del dashboard.
"""

import sqlite3

import pandas as pd

from config import FACEBOOK_DB, TIKTOK_DB


def _norm_plataforma(plataforma):
    p = str(plataforma or "ambas").strip().lower()
    if p.startswith("face") or p == "fb":
        return "facebook"
    if p.startswith("tik") or p == "tk":
        return "tiktok"
    return "ambas"


def _filtra(df, col, ini, fin):
    if df is None or df.empty or col not in df.columns:
        return df if df is not None else pd.DataFrame()
    fechas = pd.to_datetime(df[col], errors="coerce")
    mask = (fechas >= pd.Timestamp(ini)) & (fechas <= pd.Timestamp(fin))
    return df[mask].copy()


def emocional_facebook(ini, fin, db_path=None):
    """Score emocional e indice de enojo NATIVOS de Facebook (reacciones tipadas).

    Lee fb_engagement (score_emocional, indice_enojo, total_reacciones) y pondera
    por total_reacciones (mas reacciones = mas peso emocional). Devuelve dict con
    score_emocional, indice_enojo, peso y fuente, o None si no hay datos.
    """
    db_path = db_path or FACEBOOK_DB
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            "SELECT created_time, score_emocional, indice_enojo, total_reacciones "
            "FROM fb_engagement",
            conn,
        )
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()
    df = _filtra(df, "created_time", ini, fin)
    if df is None or df.empty:
        return None
    peso = pd.to_numeric(df["total_reacciones"], errors="coerce").fillna(0).clip(lower=0)
    total = peso.sum()
    if total <= 0:
        peso = pd.Series([1.0] * len(df), index=df.index)
        total = peso.sum()
    score = pd.to_numeric(df["score_emocional"], errors="coerce").fillna(0)
    enojo = pd.to_numeric(df["indice_enojo"], errors="coerce").fillna(0)
    return {
        "score_emocional": float((score * peso).sum() / total),
        "indice_enojo": float((enojo * peso).sum() / total),
        "peso": float(total),
        "fuente": "facebook_reacciones_tipadas",
    }


def emocional_tiktok(ini, fin, tk_db_path=None):
    """Score emocional e indice de enojo PROPIOS de TikTok (sentimiento de comentarios).

    TikTok no tiene reacciones tipadas; la unica senal afectiva real es el
    sentimiento de los comentarios. Se lee tiktok_sentimiento
    (pct_positivo / pct_negativo por video) unida a videos para datar por
    created_at, y se pondera por total_comentarios:
      indice_enojo    = pct_negativo / 100                  en [0, 1]
      score_emocional = (pct_positivo - pct_negativo) / 100  en [-1, 1]
    """
    tk_db_path = tk_db_path or TIKTOK_DB
    conn = None
    try:
        conn = sqlite3.connect(tk_db_path)
        df = pd.read_sql(
            """
            SELECT ts.video_id, ts.pct_positivo, ts.pct_negativo,
                   ts.total_comentarios, v.created_at
            FROM tiktok_sentimiento ts
            LEFT JOIN videos v ON CAST(ts.video_id AS TEXT) = CAST(v.id AS TEXT)
            """,
            conn,
        )
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()
    df = _filtra(df, "created_at", ini, fin)
    if df is None or df.empty:
        return None
    peso = pd.to_numeric(df["total_comentarios"], errors="coerce").fillna(0).clip(lower=0)
    total = peso.sum()
    if total <= 0:
        peso = pd.Series([1.0] * len(df), index=df.index)
        total = peso.sum()
    pos = pd.to_numeric(df["pct_positivo"], errors="coerce").fillna(0)
    neg = pd.to_numeric(df["pct_negativo"], errors="coerce").fillna(0)
    enojo = neg / 100.0
    score = (pos - neg) / 100.0
    return {
        "score_emocional": float((score * peso).sum() / total),
        "indice_enojo": float((enojo * peso).sum() / total),
        "peso": float(total),
        "fuente": "tiktok_sentimiento_comentarios",
    }


def metricas_emocionales(plataforma, ini, fin, fb_db=None, tk_db=None):
    """Orquesta el calculo emocional respetando el filtro de plataforma.

    Devuelve siempre un dict con score_emocional, indice_enojo, detalle, fuente
    y n_plataformas. Para "Ambas" combina ponderando por volumen (masa
    emocional): total_reacciones en FB y total_comentarios en TikTok. De este
    modo ningun indicador emocional mezcla la formula de una plataforma con los
    datos de otra.
    """
    plat = _norm_plataforma(plataforma)
    detalle = {}
    if plat in ("facebook", "ambas"):
        fb = emocional_facebook(ini, fin, fb_db)
        if fb:
            detalle["facebook"] = fb
    if plat in ("tiktok", "ambas"):
        tk = emocional_tiktok(ini, fin, tk_db)
        if tk:
            detalle["tiktok"] = tk

    if not detalle:
        return {
            "score_emocional": 0.0, "indice_enojo": 0.0,
            "detalle": {}, "fuente": "sin_datos", "n_plataformas": 0,
        }
    if len(detalle) == 1:
        only = next(iter(detalle.values()))
        return {
            "score_emocional": only["score_emocional"],
            "indice_enojo": only["indice_enojo"],
            "detalle": detalle,
            "fuente": only["fuente"],
            "n_plataformas": 1,
        }

    peso_total = sum(d["peso"] for d in detalle.values())
    if peso_total <= 0:
        n = len(detalle)
        score = sum(d["score_emocional"] for d in detalle.values()) / n
        enojo = sum(d["indice_enojo"] for d in detalle.values()) / n
    else:
        score = sum(d["score_emocional"] * d["peso"] for d in detalle.values()) / peso_total
        enojo = sum(d["indice_enojo"] * d["peso"] for d in detalle.values()) / peso_total
    return {
        "score_emocional": float(score),
        "indice_enojo": float(enojo),
        "detalle": detalle,
        "fuente": "combinado_ponderado_por_volumen",
        "n_plataformas": len(detalle),
    }
