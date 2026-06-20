"""Etiquetado geográfico de comentarios y posts."""

import sys
import os
import sqlite3
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from config import FACEBOOK_DB
from src.analyzer.zone_tagger import detectar_zona


def _asegurar_columna(conn, tabla, col="zona"):
    cur = conn.execute(f"PRAGMA table_info({tabla})")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} TEXT")
        conn.commit()


def taggear_zonas_facebook(db_path=None):
    if db_path is None:
        db_path = FACEBOOK_DB
    try:
        conn = sqlite3.connect(db_path)
    except Exception:
        return {"comentarios_taggeados": 0, "posts_taggeados": 0}

    try:
        _asegurar_columna(conn, "fb_comments", "zona")
        _asegurar_columna(conn, "fb_posts", "zona")
    except Exception:
        conn.close()
        return {"comentarios_taggeados": 0, "posts_taggeados": 0}

    n_com = 0
    try:
        rows = conn.execute(
            "SELECT comment_id, message FROM fb_comments WHERE message IS NOT NULL AND message != ''"
        ).fetchall()
        for cid, msg in rows:
            result = detectar_zona(msg)
            zona = result["zona"]
            conn.execute(
                "UPDATE fb_comments SET zona = ? WHERE comment_id = ?",
                (zona, cid),
            )
            n_com += 1
        conn.commit()
    except Exception:
        conn.commit()

    n_posts = 0
    try:
        post_rows = conn.execute(
            "SELECT post_id FROM fb_posts"
        ).fetchall()
        for (pid,) in post_rows:
            post_zona = None
            rows_z = conn.execute(
                "SELECT zona FROM fb_comments WHERE post_id = ? AND zona IS NOT NULL",
                (pid,),
            ).fetchall()
            zonas = [r[0] for r in rows_z]
            if zonas:
                post_zona, _ = Counter(zonas).most_common(1)[0]

            if not post_zona:
                post_msg = conn.execute(
                    "SELECT message FROM fb_posts WHERE post_id = ? AND message IS NOT NULL AND message != ''",
                    (pid,),
                ).fetchone()
                if post_msg:
                    result = detectar_zona(post_msg[0])
                    post_zona = result["zona"]

            conn.execute(
                "UPDATE fb_posts SET zona = ? WHERE post_id = ?",
                (post_zona, pid),
            )
            n_posts += 1
        conn.commit()
    except Exception:
        conn.commit()

    conn.close()
    return {"comentarios_taggeados": n_com, "posts_taggeados": n_posts}
