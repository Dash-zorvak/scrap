"""Edicion directa de registros (correcciones del analista).

Facebook (fb_posts/fb_comments): ahora delega a LocalStorage (T3.1/T3.2),
que es la unica puerta de escritura para estas tablas (C5).

TikTok (tabla videos en tiktok.db): se mantiene con sqlite3 directo,
fuera del alcance de C5 (ver T3.3).
"""

import os
import sqlite3

from src.config import Config
from src.storage.db import LocalStorage

_cfg = Config()
FACEBOOK_DB = _cfg.FACEBOOK_DB
TIKTOK_DB = _cfg.TIKTOK_DB

# Re-export desde LocalStorage (SSOT: src/storage/db.py)
COLUMNAS_EDITABLES = LocalStorage.COLUMNAS_EDITABLES

# Columnas editables de la tabla videos (TikTok) — fuera de alcance C5.
COLUMNAS_TIKTOK_EDITABLES = {
    "account_id", "description", "created_at", "views", "likes",
    "shares", "favorites_count", "comments_count", "post_url",
}

# Nota: bases de datos antiguas pueden conservar una columna needs_recalculo
# huérfana e inofensiva; no se elimina para evitar migraciones destructivas
# (ver C6 en plan maestro).


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
    """Actualiza columnas permitidas via LocalStorage. Lanza ValueError ante datos invalidos."""
    store = LocalStorage(db_path=_db(db_path))
    return store.update_fb_post(post_id, fields)


def delete_fb_post(post_id, db_path=None):
    """Elimina un post y sus comentarios via LocalStorage."""
    store = LocalStorage(db_path=_db(db_path))
    return store.delete_fb_post(post_id)


# ===========================================
# TikTok (tabla videos en tiktok.db) — fuera de alcance C5
# ===========================================

# NOTA DE ALCANCE (plan maestro, Fase 3 / C5): la unificacion de persistencia
# (C5) cubre exclusivamente fb_posts/fb_comments. Este modulo (TikTok) queda
# fuera de alcance en esta fase; se recomienda aplicar el mismo patron
# (LocalStorage + validacion + audit_log) en un plan posterior, no incluido aqui.


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
