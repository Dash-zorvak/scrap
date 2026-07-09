import sqlite3
import logging

logger = logging.getLogger(__name__)

SCHEMA_VIDEOS = """CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    account_id INTEGER,
    description TEXT,
    created_at TEXT,
    views INTEGER,
    likes INTEGER,
    shares INTEGER,
    favorites_count INTEGER,
    comments_count INTEGER,
    post_url TEXT
)"""

SCHEMA_COMMENTS = """CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    video_id TEXT,
    username TEXT,
    text TEXT,
    likes INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    created_at TEXT
)"""


def _ensure_tiktok_schema(conn: sqlite3.Connection):
    existing = conn.execute("PRAGMA table_info(videos)").fetchall()
    if not existing:
        conn.execute(SCHEMA_VIDEOS)
    else:
        cols = {row[1] for row in existing}
        if "post_url" not in cols:
            conn.execute("ALTER TABLE videos ADD COLUMN post_url TEXT")
    existing = conn.execute("PRAGMA table_info(comments)").fetchall()
    if not existing:
        conn.execute(SCHEMA_COMMENTS)


def insertar_video(conn: sqlite3.Connection, datos: dict, video_id: str) -> bool:
    try:
        _ensure_tiktok_schema(conn)
        comentarios = datos.get("comentarios") or []
        comments_count = datos.get("comments_count") or len(comentarios)
        conn.execute(
            """INSERT OR REPLACE INTO videos
               (id, account_id, description, created_at, views, likes,
                shares, favorites_count, comments_count, post_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                video_id,
                datos.get("account_id"),
                datos.get("description", ""),
                datos.get("created_at"),
                datos.get("views", 0) or 0,
                datos.get("likes", 0) or 0,
                datos.get("shares", 0) or 0,
                datos.get("favorites_count", 0) or 0,
                comments_count,
                datos.get("post_url") or None,
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error insertando video {video_id}: {e}")
        return False


def insertar_comentario_tiktok(conn: sqlite3.Connection, comment_id: str, video_id: str, texto: str) -> bool:
    try:
        _ensure_tiktok_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO comments (id, video_id, text) VALUES (?, ?, ?)",
            (comment_id, video_id, texto),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error insertando comentario TikTok {comment_id}: {e}")
        return False


def obtener_ids_videos(conn: sqlite3.Connection) -> set:
    try:
        _ensure_tiktok_schema(conn)
        rows = conn.execute("SELECT id FROM videos").fetchall()
        return {r[0] for r in rows}
    except Exception as e:
        logger.error(f"Error leyendo ids de videos: {e}")
        return set()
