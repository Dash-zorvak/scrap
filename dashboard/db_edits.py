"""Edición directa de fb_posts (correcciones del analista), vía sqlite3.

Se mantiene aparte de src/storage/db.py (modelo SQLAlchemy usado en la ingesta)
para no tocar el flujo de carga. Cubre tres cosas:
  - update_fb_post: corregir campos de un registro (p.ej. el autor/página).
  - delete_fb_post: borrar un registro y sus comentarios.
  - leer_post: leer la fila completa (incluye cares_count, que get_fb_post no
    devuelve) para alimentar correctamente las métricas del informe.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import FACEBOOK_DB  # type: ignore
except Exception:
    FACEBOOK_DB = os.getenv("FACEBOOK_DB", "facebook.db")

COLUMNAS_EDITABLES = {
    "page_name", "page_id", "message", "post_url", "sentiment",
    "topic_category", "zona", "source", "likes_count", "loves_count",
    "cares_count", "hahas_count", "wows_count", "sads_count", "angrys_count",
    "comments_count", "shares_count", "views_count", "sentiment_score",
    "created_time",
}


def _db(db_path=None):
    return db_path or os.getenv("FACEBOOK_DB", "") or FACEBOOK_DB


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
    """Actualiza columnas permitidas de un post. Devuelve True si cambió algo."""
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
        conn.commit()
        return cur.rowcount > 0
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
