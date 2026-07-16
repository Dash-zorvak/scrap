"""Edicion directa de registros (correcciones del analista).

Facebook (fb_posts/fb_comments): delega a LocalStorage (T3.1/T3.2),
que es la unica puerta de escritura para estas tablas (C5).

TikTok (tabla videos en tiktok.db): delega a TikTokStorage con audit_log.

Externos (tabla external_posts en externos.db): delega a ExternosStorage con audit_log.
"""

import os
import sqlite3

from src.config import Config
from src.storage.db import (
    LocalStorage, TikTokStorage, ExternosStorage,
    COLUMNAS_TIKTOK_EDITABLES,
)

_cfg = Config()
FACEBOOK_DB = _cfg.FACEBOOK_DB
TIKTOK_DB = _cfg.TIKTOK_DB
EXTERNOS_DB = _cfg.EXTERNOS_DB

# Re-export desde LocalStorage (SSOT: src/storage/db.py)
COLUMNAS_EDITABLES = LocalStorage.COLUMNAS_EDITABLES

COLUMNAS_EXTERNOS_POST_EDITABLES = {
    "page_name", "page_url", "message", "created_time",
    "total_reactions", "comments_count", "post_url", "source",
}


def _db(db_path=None):
    return db_path or os.getenv("FACEBOOK_DB", "") or FACEBOOK_DB


def _db_tiktok(db_path=None):
    return db_path or os.getenv("TIKTOK_DB", "") or TIKTOK_DB


def _db_externos(db_path=None):
    return db_path or os.getenv("EXTERNOS_DB", "") or EXTERNOS_DB


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
# TikTok — delega a TikTokStorage con audit_log
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
    """Actualiza columnas permitidas via TikTokStorage. Lanza ValueError ante datos invalidos."""
    store = TikTokStorage(db_path=_db_tiktok(db_path))
    try:
        return store.update_video(video_id, fields)
    finally:
        store.close()


def delete_video_tiktok(video_id, db_path=None):
    """Elimina un video y sus comentarios via TikTokStorage."""
    store = TikTokStorage(db_path=_db_tiktok(db_path))
    try:
        return store.delete_video(video_id)
    finally:
        store.close()


# ===========================================
# Externos — delega a ExternosStorage con audit_log
# ===========================================


def leer_posts_externos(limit=500, offset=0, db_path=None):
    """Devuelve los posts externos como lista de dicts."""
    conn = sqlite3.connect(_db_externos(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM external_posts ORDER BY created_time DESC LIMIT ? OFFSET ?",
            (int(limit), int(offset)),
        ).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    return [dict(r) for r in rows]


def update_post_externo(post_id, fields, db_path=None):
    """Actualiza columnas permitidas via ExternosStorage. Lanza ValueError ante datos invalidos."""
    store = ExternosStorage(db_path=_db_externos(db_path))
    try:
        return store.update_post(post_id, fields)
    finally:
        store.close()


def delete_post_externo(post_id, db_path=None):
    """Elimina un post y sus comentarios via ExternosStorage."""
    store = ExternosStorage(db_path=_db_externos(db_path))
    try:
        return store.delete_post(post_id)
    finally:
        store.close()
