"""Edicion directa de registros (correcciones del analista), via sqlite3.

Se mantiene aparte de src/storage/db.py (modelo SQLAlchemy usado en la ingesta)
para no tocar el flujo de carga. Cubre:
  - Facebook (tabla fb_posts):
      update_fb_post / delete_fb_post / leer_post.
  - TikTok (tabla videos en tiktok.db):
      leer_videos_tiktok / update_video_tiktok / delete_video_tiktok.
  leer_post lee la fila completa (incluye cares_count, que get_fb_post no
  devuelve) para alimentar correctamente las metricas del informe.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import FACEBOOK_DB, TIKTOK_DB  # type: ignore
except Exception:
    FACEBOOK_DB = os.getenv("FACEBOOK_DB", "facebook.db")
    TIKTOK_DB = os.getenv("TIKTOK_DB", "tiktok.db")

COLUMNAS_EDITABLES = {
    "page_name", "page_id", "message", "post_url", "sentiment",
    "topic_category", "zona", "source", "likes_count", "loves_count",
    "cares_count", "hahas_count", "wows_count", "sads_count", "angrys_count",
    "comments_count", "shares_count", "views_count", "sentiment_score",
    "created_time",
}

# Columnas editables de la tabla videos (TikTok).
COLUMNAS_TIKTOK_EDITABLES = {
    "account_id", "description", "created_at", "views", "likes",
    "shares", "favorites_count", "comments_count", "post_url",
}

# Columnas de fb_posts que, si se corrigen manualmente, invalidan el
# engagement ya calculado de ese post (D24) y deben disparar un recalculo
# en el próximo procesamiento del pipeline de engagement.
COLUMNAS_ENGAGEMENT_FB = {
    "likes_count", "loves_count", "cares_count", "hahas_count", "wows_count",
    "sads_count", "angrys_count", "comments_count",
}

# Lo mismo para la tabla videos (TikTok).
COLUMNAS_ENGAGEMENT_TIKTOK = {
    "views", "likes", "shares", "favorites_count", "comments_count",
}


def _marcar_recalculo(conn, tabla, col_id, valor_id):
    """Agrega needs_recalculo si falta y marca la fila para reproceso."""
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
    if "needs_recalculo" not in cols:
        conn.execute(f"ALTER TABLE {tabla} ADD COLUMN needs_recalculo INTEGER DEFAULT 0")
    conn.execute(
        f"UPDATE {tabla} SET needs_recalculo = 1 WHERE {col_id} = ?", (str(valor_id),)
    )


def _db(db_path=None):
    return db_path or os.getenv("FACEBOOK_DB", "") or FACEBOOK_DB


def _db_tiktok(db_path=None):
    return db_path or os.getenv("TIKTOK_DB", "") or TIKTOK_DB


def leer_post(post_id, db_path=None):
    """Devuelve la fila completa de fb_posts como dict, o None."""
    conn = sqlite3.connect(_db(db_path))
    conn.row_factory = sqlite3.Row
    try:
        r = conn.execute(
            "SELECT * FROM fb_posts WHERE post_id = ?", (str(post_id),)
        ).fetchone()
    except Exception:
        r = None
    finally:
        conn.close()
    return dict(r) if r else None


def update_fb_post(post_id, fields, db_path=None):
    """Actualiza columnas permitidas de un post. Devuelve True si cambio algo."""
    campos = {k: v for k, v in (fields or {}).items() if k in COLUMNAS_EDITABLES}
    if not campos:
        return False
    sets = ", ".join(f'"{k}" = ?' for k in campos)
    valores = list(campos.values()) + [str(post_id)]
    conn = sqlite3.connect(_db(db_path))
    try:
        cur = conn.execute(
            f"UPDATE fb_posts SET {sets} WHERE post_id = ?", valores
        )
        cambio = cur.rowcount > 0
        # D24: si la correccion toca algun campo que afecta el engagement ya
        # calculado, marcar el post para que se recalcule en la siguiente
        # corrida del pipeline de engagement en vez de quedar congelado con el
        # valor anterior a la correccion.
        if cambio and (set(campos.keys()) & COLUMNAS_ENGAGEMENT_FB):
            _marcar_recalculo(conn, "fb_posts", "post_id", post_id)
        conn.commit()
        return cambio
    except Exception:
        return False
    finally:
        conn.close()


def delete_fb_post(post_id, db_path=None):
    """Elimina un post y sus comentarios. Devuelve True si no hubo error."""
    conn = sqlite3.connect(_db(db_path))
    try:
        conn.execute("DELETE FROM fb_comments WHERE post_id = ?", (str(post_id),))
        conn.execute("DELETE FROM fb_posts WHERE post_id = ?", (str(post_id),))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ===========================================
# TikTok (tabla videos en tiktok.db)
# ===========================================

def leer_videos_tiktok(limit=500, offset=0, db_path=None):
    """Devuelve los videos de TikTok como lista de dicts (mas recientes primero)."""
    conn = sqlite3.connect(_db_tiktok(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (int(limit), int(offset)),
        ).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    return [dict(r) for r in rows]


def update_video_tiktok(video_id, fields, db_path=None):
    """Actualiza columnas permitidas de un video. Devuelve True si cambio algo."""
    campos = {k: v for k, v in (fields or {}).items() if k in COLUMNAS_TIKTOK_EDITABLES}
    if not campos:
        return False
    sets = ", ".join(f'"{k}" = ?' for k in campos)
    valores = list(campos.values()) + [str(video_id)]
    conn = sqlite3.connect(_db_tiktok(db_path))
    try:
        cur = conn.execute(
            f"UPDATE videos SET {sets} WHERE id = ?", valores
        )
        cambio = cur.rowcount > 0
        if cambio and (set(campos.keys()) & COLUMNAS_ENGAGEMENT_TIKTOK):
            _marcar_recalculo(conn, "videos", "id", video_id)
        conn.commit()
        return cambio
    except Exception:
        return False
    finally:
        conn.close()


def delete_video_tiktok(video_id, db_path=None):
    """Elimina un video y sus comentarios. Devuelve True si no hubo error."""
    conn = sqlite3.connect(_db_tiktok(db_path))
    try:
        conn.execute("DELETE FROM comments WHERE video_id = ?", (str(video_id),))
        conn.execute("DELETE FROM videos WHERE id = ?", (str(video_id),))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
