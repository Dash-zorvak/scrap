import os
import sqlite3
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard import modulo3_engagement as m3
from dashboard import db_edits


def _crear_db_facebook(path, posts):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE fb_posts (
            post_id TEXT PRIMARY KEY, page_name TEXT, created_time TEXT, message TEXT,
            likes_count INTEGER, loves_count INTEGER, cares_count INTEGER,
            hahas_count INTEGER, wows_count INTEGER, sads_count INTEGER,
            angrys_count INTEGER, comments_count INTEGER
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO fb_posts (post_id, page_name, created_time, message,
                              likes_count, loves_count, cares_count, hahas_count, wows_count,
                              sads_count, angrys_count, comments_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        posts,
    )
    conn.commit()
    conn.close()


def _crear_db_tiktok(path, videos):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE videos (
            id TEXT PRIMARY KEY, account_id INTEGER, description TEXT, created_at TEXT,
            views INTEGER, likes INTEGER, shares INTEGER, favorites_count INTEGER,
            comments_count INTEGER
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO videos (id, account_id, description, created_at, views, likes,
                            shares, favorites_count, comments_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        videos,
    )
    conn.commit()
    conn.close()


def test_fb_correccion_manual_dispara_recalculo(tmp_path, monkeypatch):
    db = str(tmp_path / "facebook.db")
    _crear_db_facebook(db, [
        ("p1", "Alcaldía de Santa Ana", "2026-01-01 10:00:00", "hola",
         10, 1, 1, 0, 0, 0, 0, 2),
    ])
    monkeypatch.setattr(m3, "FB_PAGES_OFICIALES", ["Alcaldía de Santa Ana"])
    m3.procesar_facebook(fb_db=db)

    conn = sqlite3.connect(db)
    total_antes = conn.execute(
        "SELECT total_reacciones FROM fb_engagement WHERE post_id = 'p1'"
    ).fetchone()[0]
    conn.close()
    assert total_antes == 12

    ok = db_edits.update_fb_post("p1", {"likes_count": 100}, db_path=db)
    assert ok is True

    conn = sqlite3.connect(db)
    flag = conn.execute(
        "SELECT needs_recalculo FROM fb_posts WHERE post_id = 'p1'"
    ).fetchone()[0]
    conn.close()
    assert flag == 1

    m3.procesar_facebook(fb_db=db)

    conn = sqlite3.connect(db)
    n_filas = conn.execute("SELECT COUNT(*) FROM fb_engagement WHERE post_id = 'p1'").fetchone()[0]
    total = conn.execute("SELECT total_reacciones FROM fb_engagement WHERE post_id = 'p1'").fetchone()[0]
    flag_final = conn.execute("SELECT needs_recalculo FROM fb_posts WHERE post_id = 'p1'").fetchone()[0]
    conn.close()
    assert n_filas == 1
    assert total == 102
    assert flag_final == 0


def test_fb_correccion_de_texto_no_dispara_recalculo(tmp_path):
    db = str(tmp_path / "facebook.db")
    _crear_db_facebook(db, [
        ("p1", "Alcaldía de Santa Ana", "2026-01-01 10:00:00", "hola",
         10, 1, 1, 0, 0, 0, 0, 2),
    ])
    ok = db_edits.update_fb_post("p1", {"message": "texto corregido"}, db_path=db)
    assert ok is True
    conn = sqlite3.connect(db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(fb_posts)").fetchall()}
    flag = None
    if "needs_recalculo" in cols:
        flag = conn.execute("SELECT needs_recalculo FROM fb_posts WHERE post_id = 'p1'").fetchone()[0]
    conn.close()
    assert not flag


def test_fb_sin_posts_marcados_no_reprocesa_nada(tmp_path, monkeypatch):
    db = str(tmp_path / "facebook.db")
    _crear_db_facebook(db, [
        ("p1", "Alcaldía de Santa Ana", "2026-01-01 10:00:00", "hola",
         10, 1, 1, 0, 0, 0, 0, 2),
    ])
    monkeypatch.setattr(m3, "FB_PAGES_OFICIALES", ["Alcaldía de Santa Ana"])
    m3.procesar_facebook(fb_db=db)
    resultado = m3.procesar_facebook(fb_db=db)
    assert resultado.empty


def test_tiktok_correccion_manual_dispara_recalculo(tmp_path):
    db = str(tmp_path / "tiktok.db")
    _crear_db_tiktok(db, [
        ("v1", 1, "video de prueba", "2026-01-01 10:00:00", 100, 10, 2, 1, 3),
    ])
    m3.procesar_tiktok(tk_db=db)

    conn = sqlite3.connect(db)
    total_antes = conn.execute(
        "SELECT engagement_total FROM tiktok_engagement WHERE id = 'v1'"
    ).fetchone()[0]
    conn.close()
    assert total_antes == 16

    ok = db_edits.update_video_tiktok("v1", {"likes": 50}, db_path=db)
    assert ok is True

    m3.procesar_tiktok(tk_db=db)

    conn = sqlite3.connect(db)
    n_filas = conn.execute("SELECT COUNT(*) FROM tiktok_engagement WHERE id = 'v1'").fetchone()[0]
    total = conn.execute("SELECT engagement_total FROM tiktok_engagement WHERE id = 'v1'").fetchone()[0]
    conn.close()
    assert n_filas == 1
    assert total == 56
