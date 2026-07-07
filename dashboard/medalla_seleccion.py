"""Selección de la «medalla»: sugerencia automática + aprendizaje por ejemplos.

Puntúa los posts oficiales del alcalde por tracción positiva neta y sugiere el
mejor candidato del período. La decisión final es del analista (aprobación manual
en el editor). El historial de aprobaciones/rechazos (medalla_store) se usa como
ejemplos para afinar la sugerencia mediante un re-ranking opcional con el LLM.

Reglas de tracción (acordadas):
  positivas = me encanta + me importa + me asombra
  negativas = me enoja + me entristece    (me divierte queda neutral)
  impresiones_est = reacciones / 0.05 (conservador) y / 0.02 (optimista)
"""

import logging
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import FACEBOOK_DB, EXTERNOS_DB, FB_PAGES_OFICIALES  # type: ignore
except Exception:
    FACEBOOK_DB = os.getenv("FACEBOOK_DB", "facebook.db")
    EXTERNOS_DB = os.getenv("EXTERNOS_DB", "externos.db")
    FB_PAGES_OFICIALES = ["Alcaldía de Santa Ana", "Gustavo Acevedo"]

from dash_periodos import rango_periodo  # noqa: E402
import medalla_store  # noqa: E402

try:
    from llm_groq import chat_texto, llm_disponible  # type: ignore
except Exception:  # el LLM es opcional; sin él se usa solo el heurístico
    def chat_texto(*a, **k):
        return ""

    def llm_disponible():
        return False


logger = logging.getLogger(__name__)


# Pesos del score heurístico de ranking.
PESOS = {
    "loves_count": 1.0, "cares_count": 1.0, "wows_count": 0.8,
    "shares_count": 1.5, "comments_count": 0.5, "likes_count": 0.1,
    "sads_count": -0.6, "angrys_count": -0.7,
}


def _i(row, k):
    try:
        return int(row.get(k) or 0)
    except Exception:
        return 0


def metricas_post(post):
    """Calcula las métricas de tracción para un post (mismas reglas del informe)."""
    positivas = _i(post, "loves_count") + _i(post, "cares_count") + _i(post, "wows_count")
    negativas = _i(post, "sads_count") + _i(post, "angrys_count")
    total = (
        _i(post, "likes_count") + _i(post, "loves_count") + _i(post, "cares_count")
        + _i(post, "hahas_count") + _i(post, "wows_count") + _i(post, "sads_count")
        + _i(post, "angrys_count")
    )
    comentarios = _i(post, "comments_count")
    compartidos = _i(post, "shares_count")
    engagement = total + comentarios + compartidos
    return {
        "positivas": positivas,
        "negativas": negativas,
        "total_reacciones": total,
        "comentarios": comentarios,
        "compartidos": compartidos,
        "engagement": engagement,
        "impresiones_conservador": int(round(total / 0.05)) if total else 0,
        "impresiones_optimista": int(round(total / 0.02)) if total else 0,
    }


def score_post(post):
    return sum(w * _i(post, k) for k, w in PESOS.items())


def _leer_posts_fb(inicio, fin, db_path=None):
    db = db_path or FACEBOOK_DB
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM fb_posts WHERE created_time IS NOT NULL "
            "AND created_time >= ? AND created_time <= ?",
            (inicio.strftime("%Y-%m-%d 00:00:00"), fin.strftime("%Y-%m-%d 23:59:59")),
        ).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    return [dict(r) for r in rows]


def sugerir_candidatos(periodo, fecha_ref=None, top=8, db_path=None,
                       solo_oficiales=True):
    """Devuelve (inicio, fin, candidatos) ordenados por score descendente.

    Cada candidato incluye '_score' y '_metricas'.
    """
    inicio, fin = rango_periodo(periodo, fecha_ref=fecha_ref)
    posts = _leer_posts_fb(inicio, fin, db_path)
    if solo_oficiales:
        oficiales = [p for p in posts if (p.get("page_name") or "") in FB_PAGES_OFICIALES]
        if not oficiales and posts:
            logger.warning(
                "No se encontraron posts oficiales en el período; "
                "se usarán %d posts no oficiales como candidatos", len(posts)
            )
        posts = oficiales or posts
    for p in posts:
        p["_score"] = score_post(p)
        p["_metricas"] = metricas_post(p)
    posts.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return inicio, fin, posts[:top]


def sugerir_no_traccion(inicio, fin, top=3, db_path=None, solo_oficiales=True):
    """Sugiere las publicaciones oficiales de MENOR tracción del período.

    Sirve como punto de partida (editable en el panel) para la sección
    «contenido que no traduce tracción a pesar de excelentes imágenes». Devuelve
    una lista de posts (dict) con '_score' y '_metricas', de menor a mayor score.
    """
    posts = _leer_posts_fb(inicio, fin, db_path)
    if solo_oficiales:
        oficiales = [p for p in posts if (p.get("page_name") or "") in FB_PAGES_OFICIALES]
        if not oficiales and posts:
            logger.warning(
                "No se encontraron posts oficiales en el período; "
                "se usarán %d posts no oficiales como candidatos", len(posts)
            )
        posts = oficiales or posts
    for p in posts:
        p["_score"] = score_post(p)
        p["_metricas"] = metricas_post(p)
    posts.sort(key=lambda x: x.get("_score", 0))
    return posts[:top]


def recomendacion_ia(candidatos, db_path=None, max_tokens=400):
    """Texto breve de recomendación del LLM, afinado con ejemplos previos.

    Honesto: NO entrena un modelo; usa las aprobaciones/rechazos anteriores como
    ejemplos (few-shot) para que la sugerencia se parezca al criterio del analista.
    Devuelve cadena vacía si el LLM no está disponible.
    """
    if not candidatos or not llm_disponible():
        return ""
    ejemplos = medalla_store.get_ejemplos_feedback(limit=12, db_path=db_path)
    lineas_ej = []
    for e in ejemplos:
        f = e.get("features") or {}
        lineas_ej.append(
            f"- decision={e.get('decision')} positivas={f.get('positivas')} "
            f"negativas={f.get('negativas')} compartidos={f.get('compartidos')} "
            f"nota={(e.get('nota') or '')[:80]}"
        )
    lineas_cand = []
    for i, c in enumerate(candidatos[:8]):
        m = c.get("_metricas") or metricas_post(c)
        lineas_cand.append(
            f"[{i}] pagina={c.get('page_name')} positivas={m['positivas']} "
            f"negativas={m['negativas']} compartidos={m['compartidos']} "
            f"comentarios={m['comentarios']} mensaje={(c.get('message') or '')[:90]}"
        )
    prompt = (
        "Eres analista de comunicacion politica. Elige cual publicacion es la mejor "
        "'medalla' (mayor traccion positiva real, no solo alcance) y explica en 2-3 "
        "frases por que. Aprende del criterio de decisiones anteriores.\n\n"
        "Decisiones anteriores del analista:\n" + ("\n".join(lineas_ej) or "(sin historial)")
        + "\n\nCandidatos del periodo:\n" + "\n".join(lineas_cand)
        + "\n\nResponde indicando el indice recomendado y la justificacion."
    )
    try:
        return chat_texto(prompt, max_tokens=max_tokens, temperature=0.3)[0] or ""
    except Exception:
        return ""


def listar_externos(inicio=None, fin=None, db_path=None):
    """Lista posts de páginas externas (medios) para marcar las réplicas."""
    db = db_path or EXTERNOS_DB
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        if inicio and fin:
            rows = conn.execute(
                "SELECT post_id, page_name, total_reactions, comments_count, "
                "post_url, created_time, message FROM external_posts "
                "WHERE created_time >= ? AND created_time <= ? "
                "ORDER BY total_reactions DESC",
                (inicio.strftime("%Y-%m-%d 00:00:00"),
                 fin.strftime("%Y-%m-%d 23:59:59")),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT post_id, page_name, total_reactions, comments_count, "
                "post_url, created_time, message FROM external_posts "
                "ORDER BY total_reactions DESC"
            ).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    return [dict(r) for r in rows]


def externos_por_ids(ids, db_path=None):
    """Devuelve los posts externos cuyos post_id estén en 'ids' (para el informe)."""
    ids = [str(x) for x in (ids or [])]
    if not ids:
        return []
    db = db_path or EXTERNOS_DB
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        marcas = ",".join("?" for _ in ids)
        rows = conn.execute(
            "SELECT post_id, page_name, total_reactions, comments_count, post_url "
            "FROM external_posts WHERE post_id IN (%s)" % marcas,
            ids,
        ).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    orden = {pid: i for i, pid in enumerate(ids)}
    out = [dict(r) for r in rows]
    out.sort(key=lambda r: orden.get(str(r.get("post_id")), 999))
    return out
